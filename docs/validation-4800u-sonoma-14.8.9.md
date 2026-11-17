# 测试验证文档：Renoir 4800U + macOS 14.8.9（Darwin 23）

本文档供使用方拉取本仓库代码后，在 **AMD Ryzen 7 4800U（Renoir，PCI `1002:1636`）+ macOS 14.8.9（23J631）** 上执行验证。
所有判定都以实机结果和 ioreg 证据为准，离线测试不能替代实机验收。

- 被测分支：`master`
- 被测 kext：`build/Release/NootedRed.kext`
- 参考系统：macOS 14.8.9 / 23J631，参考缓存 UUID `4C1441FD-8A54-3DC2-863D-49110B946A25`
- 显示数据：`UserSonomaSurfaceData`；视频数据：`UserSonomaVideoData`

## 1. 适用范围与前提

| 项目 | 要求 |
| --- | --- |
| iGPU | `1002:1636`（Renoir），`NRed.cpp` 走 `setRenoir()`，`enumRevision = 0x91` |
| 系统 | Darwin 23（macOS 14.x）。构建号不是 23J631 时仍会动态核验，但可能拒绝 OpenGL 页修复 |
| 依赖 | OpenCore，`Lilu >= 1.7.0`，且 Lilu 排在 NootedRed 之前 |
| 冲突 | 不要同时启用 WhateverGreen 的 AMD framebuffer 补丁 |
| 固件 | `Above 4G Decoding` 开启，CSM 关闭，UMA Frame Buffer ≥ 2 GB |

以下内容**不在本次验证范围**：Intel 平台、Apple Silicon、VCN 1 设备（`15D8`/`15DD`）、HDR、受保护视频（FairPlay）完整播放。

## 2. 构建与安装

```bash
git clone --recurse-submodules https://atomgit.com/weixin_47785647/NootedRed-dev.git
cd NootedRed-dev
git submodule update --init --recursive
xcodebuild -configuration Release -arch x86_64 build
```

产物：`build/Release/NootedRed.kext` 与 `build/Release/NootedRed-*.zip`。

安装：

1. 把 `Lilu.kext`、`NootedRed.kext` 放入 `EFI/OC/Kexts`；
2. `Kernel → Add` 中 Lilu 在前、NootedRed 在后，`MinKernel` 设 `23.0.0`、`MaxKernel` 设 `23.99.99`；
3. 重置 NVRAM 后重启。

## 3. 测试分级

必须按顺序执行，前一级不通过不要进入下一级。

| 级别 | 启动参数 | 目的 |
| --- | --- | --- |
| T0 | 无（仅加载 kext） | 确认基线可用 |
| T1 | `-NRedDisplayFix` | 验证显示修复 |
| T2 | `-NRedDisplayFix NRedECFix=1` | 验证 EC 背光（仅笔记本） |
| T3 | `-NRedDisplayFix NRedVideoFix` | 验证 VCN（实验性，最后做） |

> T2、T3 都必须在 T1 通过后执行。任一级出现 panic、黑屏、GPU restart，立即回到上一级并记录证据。

## 4. T0 基线验证

启动参数保持为空，确认 kext 已加载但补丁未启用。

```bash
kextstat | grep -i nootedred
ioreg -l | grep -E 'NRed' | head -30
```

| 编号 | 检查项 | 期望结果 | 判定 |
| --- | --- | --- | --- |
| T0-1 | 系统启动与登录 | 正常进入桌面，无 panic | □PASS □FAIL |
| T0-2 | 显卡识别 | 系统信息显示 AMD GPU，Metal 支持正常 | □PASS □FAIL |
| T0-3 | 显示修复标记 | 无 `NRedDisplayFixVersion`，或值不为 3 | □PASS □FAIL |
| T0-4 | 菜单栏与 Dock | 透明、模糊效果正常 | □PASS □FAIL |
| T0-5 | 外接显示 | 可输出，分辨率正确 | □PASS □FAIL |
| T0-6 | 睡眠唤醒 | 唤醒后画面正常 | □PASS □FAIL |

T0 全通过后才进入 T1；任一 FAIL 先排查 EFI 配置，不要继续。

## 5. T1 显示修复验证

启动参数只加 `-NRedDisplayFix`。

```bash
ioreg -l | grep -E 'NRed(DisplayFixVersion|SubmitGuard|OpenGL|FVRC|PatchCoordinator)'
```

| 编号 | 检查项 | 期望结果 | 判定 |
| --- | --- | --- | --- |
| T1-1 | 补丁启用标记 | `NRedDisplayFixVersion=3` | □PASS □FAIL |
| T1-2 | SubmitGuard 安装 | 无 `NRedSubmitGuardRejected`/`NRedSubmitGuardDynamicRejected` | □PASS □FAIL |
| T1-3 | OpenGL SE/CU | `NRedOpenGLSEApplied` 存在且为真 | □PASS □FAIL |
| T1-4 | OpenGL DualQuad | `NRedOpenGLDualQuadApplied` 存在且为真 | □PASS □FAIL |
| T1-5 | 计划核验 | `NRedOpenGLVPFPlanVerified` 为真；为假表示页内块不匹配被拒绝 | □PASS □FAIL |
| T1-6 | 位置缓存 | `NRedFVRCEnabled=1`、`NRedFVRCCacheReady=1` | □PASS □FAIL |
| T1-7 | 菜单栏混合 | 滚动、拖动无残影 | □PASS □FAIL |
| T1-8 | Metal 应用 | Safari、预览、Final Cut 等渲染正常 | □PASS □FAIL |
| T1-9 | OpenGL 应用 | 依赖 OpenGL 的应用窗口正常 | □PASS □FAIL |
| T1-10 | 连续使用 30 分钟 | 无花屏、卡顿、`timed out fence` 日志 | □PASS □FAIL |

日志检查：

```bash
log show --last 30m --predicate 'process == "kernel"' | grep -iE 'nred|timed out fence|gpuRestart'
```

若 `NRedOpenGLVPFPlanVerified` 为假，记录 `NRedOpenGLVPFRevision`、`ManifestMask`、`EvidenceMask`，这属于参考页不匹配，不是崩溃。

## 6. T2 EC 背光验证（仅笔记本）

启动参数加 `-NRedDisplayFix NRedECFix=1`。开始前先记录原始亮度。

```bash
ioreg -l | grep -A8 'NRedECBacklight'
```

| 编号 | 检查项 | 期望结果 | 判定 |
| --- | --- | --- | --- |
| T2-1 | 服务启动 | `NRedECBacklight` 的 `State` 为已运行 | □PASS □FAIL |
| T2-2 | 亮度范围 | `Maximum` 非 0，与硬件量程一致 | □PASS □FAIL |
| T2-3 | 滑块调节 | 亮度实际变化，`AppliedLevel` 跟随 | □PASS □FAIL |
| T2-4 | 快捷键调节 | F1/F2 或厂商快捷键生效 | □PASS □FAIL |
| T2-5 | 重启后 | 启动亮度不被改写 | □PASS □FAIL |
| T2-6 | 睡眠唤醒后 | 亮度可继续调节 | □PASS □FAIL |

背光无效果时不要使用 `NRedECFix=2` 强行切换；文档已说明固件返回值不能证明控制权切换。

## 7. T3 VCN 验证（实验性）

启动参数加 `-NRedDisplayFix NRedVideoFix`。此项风险最高，必须最后做。

```bash
ioreg -l | grep -E 'NRed(VCN|DRMVideo|Video)'
```

| 编号 | 检查项 | 期望结果 | 判定 |
| --- | --- | --- | --- |
| T3-1 | VCN 安装 | `Applied` 为真 | □PASS □FAIL |
| T3-2 | ABI 核验 | `ABIValidated` 为真；为假表示槽位不兼容，属预期拒绝 | □PASS □FAIL |
| T3-3 | H.264 1080p 解码 | 流畅，CPU 占用明显下降 | □PASS □FAIL |
| T3-4 | HEVC 1080p 解码 | 流畅 | □PASS □FAIL |
| T3-5 | HEVC 4K 解码 | 可播放，不绿屏、不花屏 | □PASS □FAIL |
| T3-6 | 编码 | QuickTime 或 ffmpeg 编码完成 | □PASS □FAIL |
| T3-7 | 连续播放 30 分钟 | 无卡死、无驱动复位 | □PASS □FAIL |
| T3-8 | 睡眠唤醒后重播 | 可继续硬解 | □PASS □FAIL |
| T3-9 | 受保护视频（可选） | 仅记录结果，不作为通过条件 | □记录 |

注意：

- `1636` 在文档中标注为“显式启用的实验路径，待实机验收”，`Applied` 为真不代表硬解成功，必须结合 CPU 占用与实际播放判断。
- 受保护视频（TV/Music）当前未解决黑屏问题，出现黑屏属已知限制，不计入失败。

## 8. 压力与异常记录

| 编号 | 检查项 | 判定 |
| --- | --- | --- |
| S-1 | 30 分钟 Metal 负载（窗口动画、视频、外接 4K） | □PASS □FAIL |
| S-2 | 反复睡眠/唤醒 5 次 | □PASS □FAIL |
| S-3 | 外接显示热插拔 | □PASS □FAIL |
| S-4 | 无新增 `.panic` / `.gpuRestart` | □PASS □FAIL |

证据收集：

```bash
sudo cp /Library/Logs/DiagnosticReports/*.panic ~/Desktop/nred-evidence/ 2>/dev/null
sudo cp /Library/Logs/DiagnosticReports/*.gpuRestart ~/Desktop/nred-evidence/ 2>/dev/null
ioreg -l > ~/Desktop/nred-evidence/ioreg.txt
log show --last 1h --predicate 'process == "kernel"' > ~/Desktop/nred-evidence/kernel.log
```

## 9. 回退

1. 全局关闭：启动参数加 `-NRedOff`，确认问题是否来自本插件。
2. 逐项关闭：先去掉 `-NRedVideoFix`，再去掉 `NRedECFix=1`，最后去掉 `-NRedDisplayFix`。
3. 关闭位置缓存做对照：加 `-NRedNoFVRC` 后重复 T1，确认是否与 FVRC 相关。
4. 保留 EFI 备份与上一版 `NootedRed.kext`，必要时整包回退。

## 10. 已知限制（不计入失败）

- VCN 在 `1636` 上为实验路径，四种 VCN 2.2 设备均待实机验收。
- 显示修复与 VCN 的部分站点只有离线证据，未完成三系统实机验收。
- 受保护视频黑屏与固件证书问题未解决；HDR 候选未集成。
- 构建号不是 23J631 时，OpenGL 页内块可能不匹配并被拒绝，属保守行为。
- 仓库中四个基线测试（`test_display_baseline`、`test_vpf_patch_audit`、`test_vpf_semantic_variants`、`test_vpf_display_semantic_variants`）与当前源码不同步，CI 已排除，尚未重新冻结。

## 11. 结果上报模板

```text
GPU：1002:1636 / Renoir
系统构建号：
缓存 UUID：
NootedRed kext UUID：
启动参数：
Lilu 版本：
T0：__/6 PASS
T1：__/10 PASS
T2：__/6 PASS
T3：__/8 PASS
S：__/4 PASS
异常：无 / 描述 + 时间点
证据包：ioreg.txt / kernel.log / panic / gpuRestart
结论：通过 / 部分通过 / 不通过
```

上报时请附上 `ioreg.txt`、`kernel.log` 与异常报告，便于对照代码中的核验路径定位问题。