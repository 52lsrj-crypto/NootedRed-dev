# NootedRed

macOS 上 AMD 集成显卡（Vega / Renoir / Cezanne 等 APU）的内核扩展，用于 GPU bug 修复、体验改进与硬件支持扩展。

本仓库基于 [ChefKissInc/NootedRed](https://github.com/ChefKissInc/NootedRed) 的开发快照（基线日期 2026-10-10），在其之上做了一系列实验性扩展。原项目版权归 ChefKiss 与各贡献者所有。

> [!WARNING]
> 本项目仍处于研究与开发阶段。它是现有 AMD 驱动之间的粘合层，崩溃、黑屏、卡顿都可能出现。
> 本仓库的新增功能默认全部关闭，需要显式启动参数才会启用。

## 相对上游的主要改动

- **用户态共享缓存补丁框架（VPF / DVPF）**：清单驱动的补丁描述、完整字节与引用核验、依赖规划、能力账本、私有 COW 页面事务与失败回滚。显示与视频共享同一个按 `vm_map` 串行的协调器。
- **VCN 硬件视频加速（实验性）**：`VCN.cpp` 接入 VCN 2.2 解码/编码路径，覆盖 `1636 / 1638 / 15E7 / 164C`；含 FairPlay（DRM）客户端策略与内核 ABI 槽位核验。VCN 1（`15D8 / 15DD`）尚未实现。
- **EC 背光服务**：`NRedECBacklight` 通过 ACPI `PNP0C14` 与 WMI `WMAA` 控制 EC 背光，修正 `IOACPIFamily` 依赖，并把亮度状态改为原子同步。
- **Darwin 23 / 24 / 25 统一显示修复**：OpenGL SE/CU、DualQuad、Metal SRD、LegacyBlend、ComputeScratch、SubmitGuard 共用入口与事务，按系统选择版本专属数据。
- **进程过滤与 FVRC 复用**：跳过不链接 GPU/媒体框架的基础系统命令，并记住已拒绝的共享缓存镜像，降低每次 exec 的补丁开销。
- **内核显示证据**：只读的 ioreg 属性，记录 kext、UUID、启动会话与关键判断结果，便于故障归因。
- **构建与 CI**：改为 Xcode 工程 + 子模块，测试脚本与文档大幅补充。

## 构建

环境要求：

- macOS 13 或更新版本
- Xcode 16 或更新版本（含命令行工具）
- Python 3.9 或更新版本（仅测试脚本需要）

```bash
git clone --recurse-submodules <本仓库地址>
cd NootedRed
git submodule update --init --recursive

xcodebuild -configuration Debug -arch x86_64 build
xcodebuild -configuration "Research Release" -arch x86_64 build
xcodebuild -configuration Release -arch x86_64 build
```

产物：

- `build/<Configuration>/NootedRed.kext`
- `build/<Configuration>/NootedRed-<版本>-<配置>.zip`

`Debug` 关闭优化，`Research Release` 为带优化的调试版，`Release` 才用于日常使用。

## 测试

统一入口为 `tools/run_all_tests.py`，会自动发现全部 `tools/test_*.py`：

```bash
python3 tools/run_all_tests.py --list
python3 tools/run_all_tests.py --jobs 4 --verbose
python3 tools/run_all_tests.py --strict          # CI 用：出现 SKIP 也判失败
python3 tools/run_all_tests.py --filter fvrc     # 只跑名字匹配的脚本
```

在 macOS 上会执行包含编译的完整测试；在 Linux 等缺少 `clang++` / `xcrun` 的环境里，依赖编译的脚本会被标记为 `SKIP` 而不是 `FAIL`。`test_ec_backlight_binary.py` 需要构建产物，使用 `--kext <路径>` 传入。

## 启动参数

| 参数 | 作用 | 省略时 |
| --- | --- | --- |
| `-NRedDisplayFix` | 显示修复（OpenGL / Metal / SubmitGuard） | 关闭 |
| `-NRedVideoFix` | VCN 硬件视频解码与编码 | 关闭 |
| `NRedECFix=1` | 使用固件报告的 EC 背光来源 | 关闭 |
| `NRedPatchAllProcs` | 关闭进程过滤，对所有进程打补丁 | 过滤开启 |

三个功能开关可以组合使用。旧的分项参数（`-NRedImmediateSync`、`-NRedSrdShared`、`-NRedLegacyBlend`、`-NRedComputeScratch`、`-NRedDRMVideo`、`-NRedVCN`）不再读取。

## 文档

- [NootedRed 深度分析报告（含架构总览、启动时序、崩溃链图）](docs/nootedred-deep-analysis.md)
- [启动参数](docs/boot-arguments.md)
- [共享缓存补丁框架（VPF）](docs/vpf-architecture.md) / [显示域（DVPF）](docs/dvpf-architecture.md)
- [多系统适配](docs/macos-multi-os-compat.md) / [用户态动态缓存匹配](docs/user-cache-dynamic.md)
- [VCN 接入](docs/vcn.md) / [FairPlay 兼容策略](docs/fairplay-psp-compatibility.md)
- [进程过滤与 FVRC 复用](docs/process-filter-fvrc.md) / [后续优化计划](docs/improvement-plan.md)
- [EC 背光重写](docs/ec-backlight-rewrite.md) / [故障归因](docs/ec-backlight-comparison.md)
- [内核显示证据](docs/kernel-display-evidence.md) / [兼容矩阵](docs/vpf-compatibility-matrix.md)
- [4800U + macOS 14.8.9 测试验证](docs/validation-4800u-sonoma-14.8.9.md)

## 已知限制

- VCN 与显示修复均标注为实验性，部分机型只有离线证据，未完成实机验收。
- 仅支持 x86_64；不支持 Apple Silicon，也不支持 VCN 1 设备。
- 新增功能默认关闭，遇到问题先在关闭全部新开关的状态下复现。
- 子模块 `Lilu` 与 `MacKernelSDK` 需要初始化后才能构建。
- 四个基线测试（`test_display_baseline`、`test_vpf_patch_audit`、`test_vpf_semantic_variants`、`test_vpf_display_semantic_variants`）仍记录上游快照的源码哈希与站点数，与本版本源码不同步，需要重新冻结基线后才能启用；CI 暂时排除这四项。

## 许可证与免责声明

原项目版权归 ChefKiss 所有，本项目保留其版权声明与免责条款。许可证文本见 [`LICENSE`](LICENSE)。

本项目按“原样”提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性与非侵权担保。使用本软件即表示你自行承担使用方式与后果的全部责任。项目团队不对因使用本软件造成的损坏、法律问题、数据丢失或其他后果负责。

本项目仅用于合法用途。使用者有责任遵守所有适用法律、许可证与协议，包括版权、商标与最终用户许可协议。项目团队不赞成也不支持盗版、侵权或任何违法行为。