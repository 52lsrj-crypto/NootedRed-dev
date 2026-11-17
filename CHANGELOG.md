# Change log

## v0.9.0 (15/11/2026)

基于上游 2026-10-10 快照的实验性扩展版本。新增功能默认关闭，需要启动参数显式启用。

### Enhancements

- 新增用户态共享缓存补丁框架（VPF / DVPF）：清单描述、完整字节与引用核验、依赖规划、能力账本、COW 页面事务与失败回滚。
- 新增显示/视频补丁协调器，按 `vm_map` 串行执行并复用共享缓存头读取结果。
- 新增 VCN 2.2 硬件视频解码与编码接入（`-NRedVideoFix`），覆盖 `1636 / 1638 / 15E7 / 164C`，含 FairPlay 客户端策略。
- 新增 EC 背光服务 `NRedECBacklight`（`NRedECFix=1`），通过 ACPI `PNP0C14` 与 WMI `WMAA` 控制背光。
- 显示修复统一为 `-NRedDisplayFix`，覆盖 OpenGL SE/CU、DualQuad、Metal SRD、LegacyBlend、ComputeScratch 与 SubmitGuard，并适配 Darwin 23 / 24 / 25。
- 新增进程过滤，跳过不链接 GPU/媒体框架的基础系统命令；新增 FVRC 拒绝缓存与已完成补丁 proof，降低每次 exec 的开销。
- 新增内核显示证据属性（`KernelDisplayEvidence`），记录 kext、UUID、启动会话与关键判断结果。
- 工程化：改用 Xcode 工程与 `Lilu` / `MacKernelSDK` 子模块；CI 增加 clang 静态分析任务，测试脚本统一由 `tools/run_all_tests.py` 驱动。

### Bug Fixes

- 修正 `OSBundleLibraries`：EC 服务改为依赖 `com.apple.iokit.IOACPIFamily`，不再错误声明 `AppleACPIPlatform`，避免 OpenCore 注入时符号解析失败。
- 修正 X5000 Compute 提交虚表 Hook 的偏移，跳过 Itanium ABI 的 `offset-to-top` 与 RTTI 槽位，并在写入前核对原函数地址。
- 修正 `allocateHWEngines` 的分配失败路径，失败时正确释放已分配引擎并返回 false，不再写入空指针。
- 背光亮度状态改用原子读写，避免与 EC 服务竞争。
- 移除上游 CI 中针对非官方仓库的强制中断步骤。

### Notes

- 版本号由 `0.8.10` 提升至 `0.9.0`，与 `MODULE_VERSION` 保持一致。
- VCN 与显示修复的部分站点只有离线证据，未完成全部机型实机验收。

## v0.8.10 (15/05/2026)

### Enhancements

- Further compatibility work for macOS Mojave.

### Bug Fixes

- Fix conflict of new AppleGFXHDA code with AppleALC's.

> [!NOTE]
> Use the `RELEASE` build. `RESEARCH_RELEASE` is `DEBUG` with optimisations.
> The latter two will be way slower and inefficient than the former build. Use them **only** when debugging an issue with NootedRed.

**Full Changelog**: https://github.com/ChefKissInc/NootedRed/compare/v0.8.9...v0.8.10

## v0.8.9 (15/05/2026)

### Enhancements

- Added the boot argument `-NRedNoAccel` for running FB-only.

  Primarily for debug purposes.
- Miscellaneous improvements to the PenguinWizardry SDK.
- Miscellaneous improvements to the GPUDriversAMD SDK.
- X6000FB and AppleGFXHDA compatibility with macOS Mojave.

  However, the Mojave-compatible X6000FB kext and instructions will only be released on v0.9.0!

### Bug Fixes

- Added missing call to calcAndSetVrrTimestampInfo in GFX9DCNDisplay implementation.

  This missing piece of code is needed on macOS Big Sur and newer, to tell the accelerator about the display timings.
- Fixed the max display count for Renoir to 4 also in the GFX9DCNDisplay implementation.

  I missed it in v0.8.4.

> [!NOTE]
> Use the `RELEASE` build. `RESEARCH_RELEASE` is `DEBUG` with optimisations.
> The latter two will be way slower and inefficient than the former build. Use them **only** when debugging an issue with NootedRed.

**Full Changelog**: https://github.com/ChefKissInc/NootedRed/compare/v0.8.8...v0.8.9

## v0.8.8 (12/05/2026)

### Enhancements

- Moved X6000FB VBIOS fix code out of iVega, into Hotfixes.

### Bug Fixes

- Gated `getTriageHardwareData` behind macOS Big Sur and macOS Monterey.

  It doesn't exist on macOS Catalina. Also replaced usage of `scnprintf` with `snprintf` as it may not be available there and cause an `Invalid Parameter` error when loading the kext.

> [!NOTE]
> Use the `RELEASE` build. `RESEARCH_RELEASE` is `DEBUG` with optimisations.
> The latter two will be way slower and inefficient than the former build. Use them **only** when debugging an issue with NootedRed.

**Full Changelog**: https://github.com/ChefKissInc/NootedRed/compare/v0.8.7...v0.8.8

## v0.8.7 (12/05/2026)

### Bug Fixes

- Neutralised setupBootWatermarks in X6000FB.

  This function applies some hardware quirk through the DCN watermarks on specific RDNA 1 dGPUs. On Raven the register offsets are even completely wrong and changing random DCN registers on specific ASIC revisions. So, I just neutralised the function.
- Added custom implementation for getTriageHardwareData (exists in macOS Monterey and below).

  This function prints a few DCN register values in a GPU diagnosis report, however, the offsets aren't quite matching for Raven and Renoir, along with the max display pipe count being 4.

**NOTE:** The "Research Release" and "Debug" builds will be way slower and inefficient than the "Release" build. Do not use them if not debugging an issue with the software.

**Full Changelog**: https://github.com/ChefKissInc/NootedRed/compare/v0.8.6...v0.8.7

## v0.8.6 (11/05/2026)

### Bug Fixes

- Worked around spurious kernel panic in recovery likely caused by Lilu bug.

**NOTE:** The "Research Release" and "Debug" builds will be way slower and inefficient than the "Release" build. Do not use them if not debugging an issue with the software.

**Full Changelog**: https://github.com/ChefKissInc/NootedRed/compare/v0.8.5...v0.8.6

## v0.8.5 (11/05/2026)

### Enhancements

- Cleaned up X6000FB branding code, removing the subsystem cruft and the weird "Renoir Graphics D4" and similar models.
- Specialised fallback model to "Radeon RX Raven Graphics", "Radeon RX Picasso Graphics", and "Radeon RX Renoir Graphics".

**NOTE:** The "Research Release" and "Debug" builds will be way slower and inefficient than the "Release" build. Do not use them if not debugging an issue with the software.

**Full Changelog**: https://github.com/ChefKissInc/NootedRed/compare/v0.8.4-2...v0.8.5

## v0.8.4 (10/05/2026)

### Enhancements

- New code style for improved readability.
- Some small code cleanup and optimisations.

  This includes improving and fixing up the dm_logger_write reimplementation that's enabled with `-NRedDebug`.
- Replaced useless backtrace on SMU/SMC command errors with plain logs including the command ID.
- Improved the memory type handling inside the X6000FB code.
- Replaced legacy model mechanism with its driver-native counterpart.

### Bug Fixes

- Fixed potential out-of-bounds string comparisons throughout the code.
- Fixed the waitForFunc timeout calculation in nanoseconds being implicitly truncated.
- Fixed the saved framebuffer size calculation of the X5000DCNDisplay implementation being implicitly truncated.
- Fixed copy paste error on the ARGB1555 surface format case of the X5000DCNDisplay implementation.
- Fixed the display pipe count on Renoir-based ASICs.

  Renoir and Raven both have only 4 display pipes. Not sure where I got the previous assumption of 6 for Renoir, maybe accidentally read from DCN 2.0 (Navi) instead of 2.1 (Renoir).

**NOTE:** The "Research Release" and "Debug" builds will be way slower and inefficient than the "Release" build. Do not use them if not debugging an issue with the software.

**Full Changelog**: https://github.com/ChefKissInc/NootedRed/compare/v0.8.3...v0.8.4-2

## v0.8.3 (24/12/2025)

### Enhancements

- Removed redundant `GPUDCCDisplayable` setting.
- Removed unnecessary `PP_ToolsLogSpaceSize` setting. This setting is only applicable for SMU 11.
- Removed redundant `PP_WorkLoadPolicyMask` setting. The value specified was 0, which is already the default.
- Removed `IOPCITunnelCompatible` property.
  iGPUs can't run through Thunderbolt.
- Moved SMU 12 firmware wait to separate function.
- Some TTL event handler cleanup.
- Miscellaneous firmware constant cleanup.

### Bug Fixes

- Rechecked driver settings and adapted them correctly to AMD Adrenaline's.
- Added missing `DalForceSingleDispPipeSplit` to Picasso settings.
- Removed Raven2 RLC A0 firmware. 
- Activate A0 RLC firmware only on non-Picasso or Picasso AM4.
- Disable MMHub PG as per the driver settings.
- Added missing `GPUTaskSingleChannel` accelerator setting.
  Possibly added in Sonoma or something, non-existent in Big Sur, default false, but set to true in the accelerator kexts (Navi and Vega).
- Corrected "wait for" logic.
  Corrected timeout to PP default of 2s from Linux's 100s and used IODelay instead of IOSleep.

**NOTE:** The "Research Release" and "Debug" builds will be way slower and inefficient than the "Release" build. Do not use them if not debugging an issue with the software.

**Full Changelog**: https://github.com/ChefKissInc/NootedRed/compare/v0.8.2...v0.8.3

## v0.8.2 (20/11/2025)

### Enhancements

- Code clean-up.
- Add back the `-NRedOff`, `-NRedBeta` boot arguments.

### Bug Fixes

- Fix cut off strings in `stringifyCRTHWDepth`.

**NOTE:** The "Research Release" and "Debug" builds will be way slower and inefficient than the "Release" build. Do not use them if not debugging an issue with the software.

**Full Changelog**: https://github.com/ChefKissInc/NootedRed/compare/v0.8.1...v0.8.2

## v0.8.1 (17/11/2025)

### Enhancements

- Code clean-up.
- Added debug prints for pixel mode, format, depth for display issue debugging.

### Bug Fixes

- Fixed AUX/OLED backlight code always returning failure.
- Fixed AUX/OLED brightness transition time (15 seconds -> 50 milliseconds).
- Fixed the addrlib setting `depthPipeXorDisable` being set to true on all Raven/Non-Renoir even Raven2 instead of Raven1, which was incorrect.

**NOTE:** The "Research Release" and "Debug" builds will be way slower and inefficient than the "Release" build. Do not use them if not debugging an issue with the software.

**Full Changelog**: https://github.com/ChefKissInc/NootedRed/compare/v0.8.0...v0.8.1

## v0.8.0 (15/11/2025)

After the latest major update, I consider NRed somewhat stable enough, so... here's the very first ever NRed release.

**NOTE:** The "Research Release" and "Debug" builds will be way slower and inefficient than the "Release" build. Do not use them if not debugging an issue with the software.
