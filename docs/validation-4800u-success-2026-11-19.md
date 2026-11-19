# 实机验证成功记录：Renoir 4800U + macOS 14.8.9（2026-11-19）

本文档记录一次**实机验证成功**的完整配置组合与证据，供后续回退或回归对照。
所有数据来自本机实测（`kextstat` / `ioreg` / 内核 panic 日志），非推测。

---

## 1. 结论（TL;DR）

**当前最佳配置（推荐回退目标）**：`Lilu 1.7.2` + `NootedRed 0.9.0`（CI 构建，commit `b86b41a9`），无 `-NRed*` 启动参数。
该组合于 2026-11-19 01:56 启动后**正常进入桌面**，关键属性：
`NRedKernelComputeHook=0`、`NRedSurfaceOverride=0`、`NRedDisplayFixVersion=3`、`NRedDisplayPlannerRevision=1`，
启动后无新 panic。这是目前**最新且验证通过**的版本。

**历史成功配置**：commit `db27423`（multiroute 修复版）于 00:28 成功进入桌面并稳定运行约 32 分钟，
是 0.9.0 系列在 4800U 上首次成功加载。后续 `9b35a96` 因同时关闭 getDisplayInfo + getSurfaceInfo 导致登录黑屏（issue #3），
已由 `b86b41a9` 修正为**仅关闭 getSurfaceInfo、保留 getDisplayInfo**。

> 三个已验证版本的演进：`db27423` ✅ → `9b35a96` ❌（登录黑屏）→ `b86b41a9` ✅（当前最佳）。

---

## 2. 硬件与系统

| 项目 | 值 |
|------|-----|
| 机型 | MacBook Pro 16,3 |
| CPU | AMD Ryzen 7 4800U（Renoir），系统伪装为 8-Core Intel Core i7 1.8GHz |
| iGPU | `1002:1636`，RID `0xc1`，Vega 8，VRAM 2GB，Metal 3 |
| 系统 | macOS 14.8.9（23J631），Darwin Kernel 23.6.0 |
| 引导 | OpenCore，OpenCore.efi 2024-07 版（无需更新） |

---

## 3. 成功的配置组合（回退目标）

### 3.1 Kext 版本与来源

| Kext | 版本 | bundle id | 来源 / SHA256 |
|------|------|-----------|---------------|
| Lilu | **1.7.2** | `as.vit9696.Lilu` | 官方 RELEASE 包，`Lilu-1.7.2-RELEASE.zip` |
| NootedRed | **0.9.0** | `org.ChefKiss.NootedRed` | 最新 commit `b86b41a9`，EFI 实测二进制 SHA256 `ee041e929889c466092ab9b963a6455cd6267769cab1562d51fd4f1ba7d360ea` |

该 NootedRed 构建包含的关键修复（累积）：
- `df5976a`：Renoir 默认跳过 compute 提交 Hook（`NRedKernelComputeHook`），加 `notifyGfxAccess` 判空、引擎分配救援参数
- `db27423`：所有 `routeMultiple` → `routeMultipleLong`，并检测已有 short jump 时跳过，**修复 multiroute panic（issue #1）**
- `9b35a96`：新增 `-NRedSurfaceOverride`，AddrLib 输入/输出清零
- `b86b41a9`：仅默认关闭 `getSurfaceInfo`，**保留 `getDisplayInfo`**——修复 `9b35a96` 的登录黑屏（issue #3）

### 3.2 加载证据

```
$ kextstat | grep -iE "lilu|nooted"
  57   15 0xffffff8003ce5000 0x31000   as.vit9696.Lilu (1.7.2)
  61    0 0xffffff8003f11000 0x315000  org.ChefKiss.NootedRed (0.9.0)
```

### 3.3 状态属性（ioreg）

```
NRedDisplayPlannerRevision = 1
NRedKernelComputeHook      = 0    ← Renoir 按策略关闭 compute Hook（df5976a 生效）
NRedSurfaceOverride        = 0    ← getSurfaceInfo 覆盖关闭、getDisplayInfo 保留（b86b41a9）
NRedDisplayPlannerRequested = 0
NRedDisplayFixVersion      = 3    ← 显示修复已安装
```

### 3.4 启动参数

```
-v revpatch=cpuname,sbvmm ipc_control_port_options=0 revblock=media -vi2c-force-polling
```

**无任何 `-NRed*` 参数**——所有修复都以默认方式生效。

### 3.5 config.plist 关键项

```
Kernel/Add[0] = Lilu.kext        (Enabled=true)
Kernel/Add[5] = NootedRed.kext   (Enabled=true, BundlePath=NootedRed.kext,
                                  ExecutablePath=Contents/MacOS/NootedRed)
NVRAM boot-args = （见 3.4）
```

config 只按路径注入 kext，与 bundle id 无关，因此 `org.ChefKiss.NootedRed` 可正常加载。

---

## 4. 依赖与兼容性要点

* 该 NootedRed 0.9.0 要求 `Lilu >= 1.7.0`，**必须**配 Lilu 1.7.2；回退时不要单独退回 Lilu 1.6.7。
* 若仅保留 Lilu 1.6.7，只能配回 **NootedRed 1.0.0**（`com.ChefKissInc.NootedRed`）——这是原始出厂稳定组合，能进桌面但花屏较频繁。
* Lilu 1.7.x + NootedRed 0.9.0（未修复 multiroute 的版本，如 `df5976a`）会在启动早期 panic：
  `Lilu patcher: previous plugin had short jump type on a multiroute function`（见 issue #1）。
  必须使用含 `db27423` 修复的构建。

---

## 5. 已知遗留问题（成功配置下仍存在）

即使成功进入桌面，仍观察到偶发内核 panic：

```
panic: userspace watchdog timeout: no successful checkins from WindowServer in 120 seconds
       WindowServer initialization not complete (post IOKitWaitQuiet)
```

时间戳：2026-11-18 22:23:17 与 23:04:37。根因指向 0.9.0 的 surface/display 覆盖在
WindowServer 新建 surface 时产生错误布局并触发 GFX Reset。

修复演进：
- `9b35a96` 曾同时关闭 `getDisplayInfo` + `getSurfaceInfo`，导致登录黑屏（issue #3）。
- `b86b41a9` 改为**仅关闭 getSurfaceInfo、保留 getDisplayInfo**，既避免了 surface 引起的 GFX Reset，
  又维持了显示初始化。该版本于 2026-11-19 01:56 启动成功，进入桌面且无新 panic。

另有一次 01:20:22 的 panic（`Kernel-2026-11-19-012022.panic`）发生在 b86b41a9 安装前，需后续观察。

状态：issue #2（运行时 GPU Reset）与 issue #3（登录黑屏）均待上游进一步确认是否完全解决。

---

## 6. 回退路径

本机保留的备份位于工作区：

```
工作区备份：
  efi-backup-baseline-20261118-0034/
  ├── Lilu.kext.1.7.2
  ├── NootedRed.kext.1.0.0        ← 原始稳定版（com.ChefKissInc.NootedRed）
  ├── config.plist
  ├── before-multiroute-fix-0922/ ← Lilu 1.6.7 + NootedRed 1.0.0
  └── before-surface-fix-0019/    ← Lilu 1.7.2 + NootedRed 0.9.0(db27423)

CI 产物（工作区根目录，含 kext + dSYM + zip）：
  nootedred-ci-0.9.0-multiroute-fix/   ← db27423
  nootedred-ci-0.9.0-surface-fix/      ← 9b35a96（登录黑屏，不要用）
```

回退路径：
- **回退到当前最佳版本（b86b41a9）**：从 GitHub CI 重新下载 `b86b41a9` 产物，或直接用当前 EFI 状态（已验证）。
- **回退到历史成功版本（db27423）**：把 `before-surface-fix-0019/` 里的 kext 覆盖回 `EFI/OC/Kexts/`。
- **回退到原始稳定版**：用 `Lilu.kext.1.7.2` + `NootedRed.kext.1.0.0`（能进桌面，花屏较频繁）。

> 注：EFI 分区内的历史备份（`OC-NRed-Backup-*`、`oldConfig.plist` 等）已于 2026-11-19 清理，
> 回退请依赖上述工作区备份与 CI 产物。

---

## 7. 完整验证时间线（供回归对照）

| 版本组合 | 结果 |
|----------|------|
| NootedRed 1.0.0 + Lilu 1.6.7 | 能进桌面，花屏较频繁（原始状态） |
| NootedRed 1.0.0 + Lilu 1.7.2 | 能进桌面，花屏减轻（唯一正面改善的旧组合） |
| NootedRed 0.9.0（手工/CI/`df5976a`） + Lilu 1.7.2 | 卡苹果 Logo，multiroute panic（issue #1） |
| NootedRed 0.9.0（`db27423` multiroute 修复） + Lilu 1.7.2 | ✅ 成功进桌面，稳定运行 32 分钟 |
| NootedRed 0.9.0（`9b35a96` surface 修复） + Lilu 1.7.2 | ❌ 登录黑屏（同时关闭 display/surface 覆盖，issue #3） |
| NootedRed 0.9.0（`b86b41a9` 仅关 surface） + Lilu 1.7.2 | **✅ 成功进桌面，无新 panic（当前最佳，2026-11-19 01:56）** |

相关数据文件：
* 崩溃日志分析：`崩溃日志分析报告.md`（工作区）
* bug 报告：`NootedRed-0.9.0-Lilu-multiroute-panic-bugreport.md`（工作区，已提交为 issue #1）
* 修复方案：`NootedRed-0.9.0-修复方案.md`（工作区）
