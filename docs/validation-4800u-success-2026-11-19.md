# 实机验证成功记录：Renoir 4800U + macOS 14.8.9（2026-11-19）

本文档记录一次**实机验证成功**的完整配置组合与证据，供后续回退或回归对照。
所有数据来自本机实测（`kextstat` / `ioreg` / 内核 panic 日志），非推测。

---

## 1. 结论（TL;DR）

**成功配置**：`Lilu 1.7.2` + `NootedRed 0.9.0`（CI 构建，commit `db27423`，multiroute 修复版），无 `-NRed*` 启动参数。
该组合于 2026-11-19 00:28 启动后**正常进入桌面**，`NRedKernelComputeHook=0`、`NRedDisplayFixVersion=3`，
是 0.9.0 系列在 4800U 上首次成功加载并运行。

> 注意：后续又有新提交 `9b35a96`（surface 覆盖默认关闭），安装于 00:56，尚未重启验证。
> 本记录针对的是已验证成功的 **`db27423`** 组合。

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
| NootedRed | **0.9.0** | `org.ChefKiss.NootedRed` | CI run `44349247959`，commit `db27423`，artifact `14448302398`，SHA256 `fd3f9cc08623e070b96b5379b9d994e60e1837fc12f90407a9f5cfe49c9a71e9` |

该 NootedRed 构建包含两处关键修复：
- `df5976a`：Renoir 默认跳过 compute 提交 Hook（`NRedKernelComputeHook`），加 `notifyGfxAccess` 判空、引擎分配救援参数
- `db27423`：所有 `routeMultiple` → `routeMultipleLong`，并检测已有 short jump 时跳过，**修复 multiroute panic**

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

时间戳：2026-11-18 22:23:17 与 23:04:37。根因指向 0.9.0 的 `getDisplayInfo/getSurfaceInfo` 覆盖在
WindowServer 新建 surface 时产生错误布局并触发 GFX Reset。已由提交 `9b35a96` 修复（surface 覆盖默认关闭），
该版本已安装但**尚待重启验证**。

---

## 6. 回退路径

本机保留的备份位于工作区：

```
efi-backup-baseline-20261118-0034/
├── Lilu.kext.1.7.2
├── NootedRed.kext.1.0.0        ← 原始稳定版（com.ChefKissInc.NootedRed）
├── config.plist
├── before-refixed-0.9.0-0757/
├── before-multiroute-fix-0922/ ← Lilu 1.6.7 + NootedRed 1.0.0
└── before-surface-fix-0019/    ← Lilu 1.7.2 + NootedRed 0.9.0(db27423) 【本记录的组合】
```

回退到本成功组合：把 `before-surface-fix-0019/` 里的 `Lilu.kext.1.7.2` 与
`NootedRed.kext.0.9.0-multiroute-fix` 覆盖回 `EFI/OC/Kexts/` 对应位置即可。

---

## 7. 完整验证时间线（供回归对照）

| 版本组合 | 结果 |
|----------|------|
| NootedRed 1.0.0 + Lilu 1.6.7 | 能进桌面，花屏较频繁（原始状态） |
| NootedRed 1.0.0 + Lilu 1.7.2 | 能进桌面，花屏减轻（唯一正面改善的旧组合） |
| NootedRed 0.9.0（手工/CI/`df5976a`） + Lilu 1.7.2 | 卡苹果 Logo，multiroute panic（issue #1） |
| NootedRed 0.9.0（`db27423` multiroute 修复） + Lilu 1.7.2 | **✅ 成功进桌面，属性正常（本记录）** |
| NootedRed 0.9.0（`9b35a96` surface 修复） + Lilu 1.7.2 | 已安装，待验证 |

相关数据文件：
* 崩溃日志分析：`崩溃日志分析报告.md`（工作区）
* bug 报告：`NootedRed-0.9.0-Lilu-multiroute-panic-bugreport.md`（工作区，已提交为 issue #1）
* 修复方案：`NootedRed-0.9.0-修复方案.md`（工作区）
