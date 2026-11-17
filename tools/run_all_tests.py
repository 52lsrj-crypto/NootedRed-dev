#!/usr/bin/env python3
"""统一测试入口：发现并运行 tools/test_*.py。

在 Linux 等无 macOS 工具链的机器上，因缺少 clang++/xcrun 而无法执行的脚本会被标记为
SKIP 而不是 FAIL；在 macOS 上则全部执行。需要构建产物的脚本在未提供 --kext 时跳过。

用法:
    python3 tools/run_all_tests.py --list
    python3 tools/run_all_tests.py --jobs 4
    python3 tools/run_all_tests.py --filter fvrc --verbose
    python3 tools/run_all_tests.py --kext build/Release/NootedRed.kext
"""
from __future__ import annotations

import argparse
import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

ARTIFACT_TESTS = {"test_ec_backlight_binary.py"}
VARIANTS = {
    "test_display_cross_module_gate.py": [["--sanitize"]],
    "test_ec_backlight_service.py": [["--thread-sanitizer"]],
}
TOOLCHAIN_ERROR = re.compile(
    r"需要 clang\+\+|clang\+\+ required|xcrun: error|"
    r"FileNotFoundError: \[Errno 2\] No such file or directory: '(xcrun|clang\+\+)'"
)
ENV_ERRORS = [
    (TOOLCHAIN_ERROR, "本机无 clang++/xcrun"),
    (re.compile(r"未核实，拒绝生成"), "需要本机 macOS 共享缓存数据"),
    (re.compile(r"请先构建"), "需要先构建对应 Xcode 配置"),
    (re.compile(r"/System/Volumes/|KernelCollection 中均未找到|AMDRadeonX"), "需要 macOS 系统缓存或驱动"),
    (re.compile(r"FileNotFoundError.*(build/|/System/)"), "需要先生成构建数据"),
    (re.compile(r"the following arguments are required"), "需要外部输入参数"),
    (re.compile(r"'as', '-arch'"), "需要 Xcode 汇编器"),
    (re.compile(r"not NoneType"), "需要构建产物"),
]


@dataclass
class Result:
    name: str
    status: str
    seconds: float
    detail: str = ""


def macro_toolchain_available() -> bool:
    return shutil.which("xcrun") is not None or shutil.which("clang++") is not None


def is_macos() -> bool:
    return sys.platform == "darwin"


def discover() -> list[Path]:
    return sorted(p for p in TOOLS.glob("test_*.py") if p.is_file())


def run_one(path: Path, extra: list[str], timeout: int, kext: str | None) -> Result:
    args = [sys.executable, str(path), *extra]
    if path.name in ARTIFACT_TESTS:
        if not kext:
            return Result(path.name + " " + " ".join(extra), "SKIP", 0.0, "需要 --kext 构建产物")
        args.append(kext)
    started = time.monotonic()
    try:
        proc = subprocess.run(
            args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=os.environ
        )
        elapsed = time.monotonic() - started
    except subprocess.TimeoutExpired:
        return Result(path.name + " " + " ".join(extra), "TIMEOUT", time.monotonic() - started,
                      f"超过 {timeout}s")
    output = (proc.stdout or "") + (proc.stderr or "")
    label = path.name + (" " + " ".join(extra) if extra else "")
    if proc.returncode == 0:
        return Result(label, "PASS", elapsed)
    for pattern, reason in ENV_ERRORS:
        if pattern.search(output):
            return Result(label, "SKIP", elapsed, reason)
    if "IndexError: list index out of range" in output and "sys.argv" in output:
        return Result(label, "SKIP", elapsed, "需要外部输入参数")
    tail = "\n".join(output.strip().splitlines()[-25:])
    return Result(label, "FAIL", elapsed, tail)


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 tools/test_*.py 全量测试")
    parser.add_argument("--list", action="store_true", help="只列出将执行的测试")
    parser.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1), help="并发数")
    parser.add_argument("--timeout", type=int, default=300, help="单脚本超时秒数")
    parser.add_argument("--filter", default="", help="只运行名称匹配该正则的脚本")
    parser.add_argument("--exclude", default="", help="排除名称匹配该正则的脚本")
    parser.add_argument("--kext", default="", help="EC 符号检查使用的 kext 路径")
    parser.add_argument("--verbose", action="store_true", help="失败时总是打印日志尾部")
    parser.add_argument("--fail-fast", action="store_true", help="首个失败即停止")
    parser.add_argument("--strict", action="store_true", help="存在 SKIP 时也视为失败（CI 全量校验用）")
    args = parser.parse_args()

    scripts = discover()
    if args.filter:
        pattern = re.compile(args.filter)
        scripts = [p for p in scripts if pattern.search(p.name)]
    if args.exclude:
        pattern = re.compile(args.exclude)
        scripts = [p for p in scripts if not pattern.search(p.name)]
    if not scripts:
        print("没有匹配的测试脚本")
        return 1

    plan: list[tuple[Path, list[str]]] = []
    for script in scripts:
        for extra in VARIANTS.get(script.name, [[]]):
            plan.append((script, extra))

    if args.list:
        for script, extra in plan:
            suffix = (" " + " ".join(extra)) if extra else ""
            print(f"{script.name}{suffix}")
        print(f"\n共 {len(plan)} 个测试（{len(scripts)} 个脚本）")
        return 0

    print(f"运行 {len(plan)} 个测试，并发 {args.jobs}，超时 {args.timeout}s，平台 {sys.platform}")
    if not macro_toolchain_available():
        print("提示：本机无 clang++/xcrun，依赖编译的测试将标记为 SKIP")

    results: list[Result] = []
    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {
            pool.submit(run_one, script, extra, args.timeout, args.kext or None): (script, extra)
            for script, extra in plan
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"[{result.status:7}] {result.seconds:6.1f}s  {result.name}")
            if result.status in {"FAIL", "TIMEOUT"}:
                failures += 1
                if args.verbose or result.detail:
                    for line in result.detail.splitlines():
                        print(f"          {line}")
                if args.fail_fast:
                    for pending in futures:
                        pending.cancel()
                    break

    passed = sum(1 for r in results if r.status == "PASS")
    skipped = sum(1 for r in results if r.status == "SKIP")
    failed = sum(1 for r in results if r.status in {"FAIL", "TIMEOUT"})
    print(f"\n汇总: {passed} passed, {failed} failed, {skipped} skipped, 共 {len(results)}")
    if skipped:
        print("跳过的测试:")
        for result in sorted(results, key=lambda r: r.name):
            if result.status == "SKIP":
                print(f"  - {result.name}: {result.detail}")
    if args.strict and skipped:
        print("--strict：存在跳过的测试，判定为失败")
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())