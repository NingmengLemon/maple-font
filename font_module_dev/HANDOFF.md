# Handoff: Maple Mono OxygenOS 16 Font Module

## 原始任务（来自上一任 agent）

1. 写一个按优先级把 CJK 字形 merge 成一个字体文件的脚本 — 已完成
2. 调研 OxygenOS 16 (CPH2747_16.0.9.400) 字体配置应用逻辑 — 已完成，四层配置已确认
3. 在 font_module_dev/module/ 制作 Magisk/KernelSU 字体替换模块 — 实验版已可用，稳定性已验证

---

## 审阅发现的 P0 缺陷与修复

### P0-1：字体文件名不匹配

上一任生成的 XML 引用 `MapleMonoNF-AllCJK-*.ttf`（无连字符），合并输出为 `MapleMono-NF-AllCJK-*.ttf`。
→ 已通过 generate_configs.py 修复。

### P0-2：KernelSU 不挂载 system overlay

KernelSU 需要 metamodule（如 hybrid_mount）才能挂载 system 分区。
→ 用户设备已安装 hybrid_mount。已通过 device_capture/ 确认挂载有效。

### P0-3：OOS fonts_base.xml 运行时拼接

上一任的 post-fs-data.sh 用 sed 文本拼接补充 fallback fragment，会产生非法 XML。
→ 已删除；改为从实机样本生成完整四层 XML overlay。

### P0-4：自定义 update-binary 包装层

上一任手写的 update-binary 存在未初始化变量和引用问题。
→ 已替换为 Magisk 官方最小入口 + KernelSU Next 原生安装器。

---

## 当前稳定模块

### 已实机验证能正常启动、Zygisk 正常、App 兼容的配置

- **字体文件：** `fonts/NF-AllCJK/MapleMono-NF-AllCJK-*.ttf`（16 个静态 face）
- **XML 覆盖：** 四层 overlay（system/etc × 2 + system_ext/etc × 2）
  - `system/etc/font_fallback.xml`
  - `system/etc/fonts.xml`
  - `system_ext/etc/fonts_base.xml`
  - `system_ext/etc/fonts_ule.xml`
- **XML 生成器：** `generate_configs.py` — 从实机 samples/ 生成 overlay
  - CJK family 仅替换为 Maple 静态 face，不拼接 Noto fallback
  - 通用 Noto Symbols family 后固定保留系统 `Roboto-Regular.ttf`，用于罕见非 CJK / 组合附加符回退
- **构建器：** `build_module.py` — 再生 XML → 复制字体 → 校验引用 → 打包 ZIP
  - ZIP 输出：`font_module_dev/maple-font-module-v0.1.1-dev.zip`（~197.9 MiB）

### 关键环境要求（写入 DEVICE_VALIDATION.md）

1. **KernelSU Next "默认卸载模块" 必须关闭**：否则 App 进程看不到模块挂载的字体，FontManager 已下发 Maple 路径，导致 Minikin/HWUI SkData 打开失败崩溃。已通过实际日志（device_capture/）验证。
2. **hybrid_mount metamodule 必须启用**：当前活跃的 system overlay 提供者。
3. **旧 MapleMono-NF-CN-Regular 模块必须禁用**：避免同时有新旧两个模块竞争字体和 XML。

---

## 已知限制：CJK Extension G/H/I/J 无字形

### 现象

字体测试网站显示 CJK Extension G/H/I/J 为空，且无 tofu fallback。

### 根因

当前所有四个 locale 源配置（config-cn.json 等）的 `unicode.ranges` 最高只到 `U+FFEF`（BMP），不包含 supplementary-plane 范围。因此无论源字体 WenYuan 中是否有对应字形，build pipeline 都不会将其包含进输出字体。

### 源字体覆盖现状（audit_cjk_extensions.py 报告）

| 源变体 | ExtG | ExtH | ExtI | ExtJ |
|--------|------|------|------|------|
| WenYuanRoundedSCVF.ttf (CN) | 80 | 27 | 8 | 19 |
| ResourceHanRoundedJP-VF.otf (JP) | 2 | 0 | 0 | 0 |
| ChironGoRoundTCVF.ttf (TC/KR) | 27 | 23 | 1 | 35 |
| **当前输出 AllCJK** | **0** | **0** | **0** | **0** |

源字体 WenYuan_含有_ ExtG 到 J 的字形，但未被包含进构建输出，因为 locale config 没有声明这些 unicode 范围。

### 失败尝试

尝试在 CJK XML family 中将原有 Noto CJK face 拼接在 Maple face 之后以作为 fallback，会导致 bootloop（CPH2747 framework 不支持在同一 language family 中混合静态 Maple face 与带 TTC index / variable axis 的原始 face）。

### 后续方案

正确路径是在 **source/cjk/*/config-*.json** 的 `unicode.ranges` 中加入 supplementary-plane 范围后**重新构建 CJK 字体**。这需要：

1. 修改 locale config（例如在 config-cn.json 中添加 `0x2EBF0-0x2EE5F`, `0x30000-0x3134F`, `0x31350-0x323AF`, `0x323B0-0x3347F`）
2. 重新执行完整 CJK build（包括下载源字体、合并、生成输出）
3. 在模块中替换新的字体文件

注意这是**字体源范围扩展 + 重构建**任务，不是 XML 配置任务。在本地电脑完成所有构建和清理后，再打包新的模块。

**在修改任何 locale config 或重新构建字体前，先确认当前工作目录干净，不影响已实机验证能启动的模块和配置文件。**

---

## Android generic fallback experiment (passed)

The reported kaomoji `喵ᯠ  _   ̫  _ ̥ ᯄ ੭` contains more than CJK:

- U+1BE0 and U+1BC4 resolve through the preserved `NotoSansBatak-Regular.ttf` fallback.
- U+0A6D resolves through the preserved `NotoSansGurmukhi-VF.ttf` fallback.
- Maple maps U+0325 but not U+032B. U+032B is a nonspacing combining mark, so absence can look like an invisible mark rather than a tofu glyph.

An isolated module, `maple-font-roboto-fallback`, adds the existing system `Roboto-Regular.ttf` as one generic fallback immediately after `NotoSansSymbols-Regular-Subsetted.ttf` in each of the four overlays. It does **not** package Roboto, change named Maple families, or change any CJK language family.

On CPH2747, the owner installed this module and rebooted successfully. `dumpsys font`, live XML, and the Play Store process namespace confirmed the four overlays, 16 Maple assets, and the Roboto fallback. The extended Android diagnostic now inspects the actual shaped glyph font path: U+032B with an underscore selects `Roboto-Regular.ttf`, while U+0325 selects Maple. The owner confirmed the complete kaomoji renders normally.

This is a narrow, accepted compatibility fix. It must remain a generic fallback: **do not** put original Noto/SysSans faces back into any CJK language family. Full evidence and the package reconstruction details are in [FALLBACK_DIAGNOSIS.md](FALLBACK_DIAGNOSIS.md).

---

## 关键文件路径与用途

| 路径 | 用途 | 来源 |
|------|------|------|
| `merge_cjk_locales.py` | CJK locale 优先级合并脚本 | 上一任 |
| `font_module_dev/generate_configs.py` | 从实机 samples 生成模块 XML | 新写 |
| `font_module_dev/build_module.py` | 构建模块 ZIP + 校验 | 重构 |
| `scripts/tests/test_cjk_locale_merge.py` | merge 优先级 + 配置生成单测 | 新写 |
| `font_module_dev/FALLBACK_DIAGNOSIS.md` | 通用 Android fallback 调研、实机结果和安全边界 | 本次 |
| `font_module_dev/experiments/roboto-fallback/` | 已通过的 Roboto generic fallback staging 模块 | 本次 |
| `font_module_dev/experiments/maple-font-headbound.zip` | 重建的 Headbound 包，含 Roboto generic fallback | 本次（忽略的派生产物） |
| `font_module_dev/audit_cjk_extensions.py` | 只读审计源字体 Extended 区覆盖 | 新写 |
| `font_module_dev/module/system/etc/*.xml` | 生成的 system overlay | generate_configs → build_module |
| `font_module_dev/module/system_ext/etc/*.xml` | 生成的 system_ext overlay | generate_configs → build_module |
| `font_module_dev/samples/*.xml` | 从实机拉取的原始配置样本 | 实机 adb pull + exec-out |
| `font_module_dev/device_capture/` | 所有设备诊断捕获 | 实机 adb 只读命令；文件索引见 `device_capture/README.md`（目录默认忽略，不提交设备标识） |
| `font_module_dev/experiments/` | 独立指标实验 module staging | 实验状态、重建命令与安全说明见 `experiments/README.md` |
| `font_module_dev/report.md` | 调研报告 | 维护中 |
| `font_module_dev/DEVICE_VALIDATION.md` | 设备验证命令集合 | 维护中 |
| `font_module_dev/maple-font-module-v0.1.1-dev.zip` | 构建产物 | build_module.py |

---

## 已完成验证

- Ruff lint / format check 通过（generate_configs, build_module, merge_cjk_locales, test_cjk_locale_merge）
- Pyrefly type checker 通过（0 errors）
- 合并单测通过（2 tests：merge_chain 优先级映射 + 配置生成不引入额外 CJK family）
- 所有 16 个合并字体 FontTools 校验通过
- 四层 XML 均解析合法
- 模块 XML 引用与字体资产一一匹配
- 实机启动、字体生效、Zygisk 正常、Google App/普通 App 无崩溃
- KernelSU "默认卸载模块"关闭后稳定性已验证
- Roboto generic fallback 实验：四层 live XML、FontManager、Play Store namespace、Android shaping diagnostic 和目视 kaomoji 均通过

---

## Mobile vertical-metrics experiment

### Experiment setup

Two isolated test modules were built by copying the existing 16 final `NF-AllCJK` static TTFs and patching only their declared `hhea`, OS/2 Typo, and OS/2 Win vertical metrics. The real outline bounds (`head.yMin/yMax`) were intentionally retained. The generated ZIPs and staged files are under `font_module_dev/experiments/`:

| Candidate | Declared ascent/descent | Module ID | Result |
|---|---:|---|---|
| `ascent-970` | `970/-300` | `maple-font-ascent-970` | No visible improvement in affected applications |
| `ascent-950` | `950/-300` | `maple-font-ascent-950` | No visible improvement in affected applications |

The owner installed the experimental patched module(s) on the target device and reported that previously defective application layouts looked indistinguishable from the original module. This invalidates the working assumption that reducing only the final font's declared ascent is sufficient to improve the observed Android UI layout defect.

### Interpretation and next steps

The result does not prove that font metrics are irrelevant. It does show that the tested application path either ignores these patched static-table fields, derives its layout from different metrics or cached typefaces, or is dominated by glyph geometry/baseline placement and a fixed application layout. Do not promote these two patched-metric packages as a fix.

Future investigation should prioritize, in order:

1. Capture Android `Paint.FontMetricsInt` and actual text layout measurements for the original and patched fonts in a minimal test application, including `includeFontPadding` variations.
2. Verify that an experiment module is mounted and selected by the affected process after reboot; collect FontManager/typeface logs and compare font checksums as visible to the application process.
3. Compare the original system UI font's baseline and visible CJK ink bounds against Maple's CJK transform (`y_scale` and `y_shift`) rather than modifying only final vertical tables.
4. If CJK geometry is implicated, rebuild an isolated candidate from source with a conservative CJK vertical scale/shift change, then repeat the Android-side measurements before broad real-app testing.

## Android layout diagnostic (Phase A1 started)

A local-only framework Android diagnostic application is now available at `font_module_dev/android_layout_diagnostic/`. It creates fixed-height single-line, multiline, title, list-row, chat, and button-like `TextView` cases with both `includeFontPadding` states, automatic/explicit line-height cases, and logs `Paint.FontMetricsInt`, view geometry, baselines, and Android layout bounds.

- Build with `font_module_dev\\android_layout_diagnostic\\gradlew.bat -p font_module_dev\\android_layout_diagnostic assembleDebug` from `cmd.exe`.
- A Maple-active run loaded `/system/fonts/MapleMono-NF-AllCJK-Regular.ttf` explicitly (`candidate_load=success`); its Logcat report and screenshot are saved under `font_module_dev/device_capture/`. The active `sans-serif` and explicit candidate necessarily matched in that state.
- A second run after the owner disabled the module and rebooted proved that the Maple file was no longer mounted. It recorded original-system `sans-serif` metrics of `top/ascent/descent/bottom = -67/-58/15/18` at 20sp, compared with Maple's `-83/-64/19/48` at the same size. The automatic single-line view was 90 px for the system face and 83 px for Maple. The captured reference-only report is `layout-diagnostic-reference.txt`.
- To compare both faces in one process while Maple remains disabled, the module's Regular TTF was copied into the diagnostic app's private `files/` directory using `adb` plus `run-as`; `layout-diagnostic-reference-with-maple.txt` proves its `candidate_load=success`. It confirms the metric differences above across all fixed-height cases. This private-file staging is diagnostic-only and does not modify the module or system partitions.
- The evidence establishes that Android reads materially different metrics and produces different baseline/layout positions. It does not yet reproduce the failing third-party layout or establish that a final-table metric patch changes the observed behavior. Phase A1 should next add a concrete reproduction matching an affected app before source geometry experiments.

### QQ private-chat header reproduction

The owner supplied a repeatable affected page: QQ private chat with `柠檬味的凝萌`, where the status under the nickname is clipped. The collected UI hierarchies make the failure mechanically visible:

| State | Nickname bounds | Status `ViewFlipper` bounds | Header parent bounds |
|---|---|---|---|
| Original system font | `y=163..231` (68 px) | `y=231..267` (36 px) | `y=141..290` (149 px) |
| Maple active | `y=163..270` (107 px) | `y=270..290` (20 px) | `y=141..290` (149 px) |

The parent header remains a fixed 149 px, while the nickname allocation grows by 39 px. The lower status area loses 16 px and terminates exactly at the parent bottom, which matches the observed clipping. This is direct evidence that the QQ failure is layout-space exhaustion caused by the system font's changed text layout, not merely a visual glyph-bound issue.

The diagnostic app now includes a QQ-shaped stacked/header case and a pixel-positioned overlap case derived from the captured hierarchy. With Maple active, the 30sp title's Android layout requires 124 px against 111 px for the original system face; its `Paint.FontMetricsInt` is `-124/-96/28/72` (`top/ascent/descent/bottom`) versus `-100/-88/23/26` for the original system face. The app's 20 px status strip also overflows in both fonts by construction, but Maple's calculated layout is 58 px versus the original 52 px. The actual QQ allocation delta is larger because QQ's own title text size and layout rules differ from the diagnostic approximation.

A FontTools audit captures the structural mismatch: Maple Regular declares `hhea/Typo = 1020/-300` (1320 units total), whereas the original `SysSans-Hans-Regular.ttf` declares `hhea = 928/-244` (1172 units total). Maple's outlines also extend to `1309/-761`; reducing only the final declared tables cannot make those outlines physically more compact and has already shown no visible fix in the preceding `ascent-970` / `ascent-950` module experiments.

This conclusion was independently confirmed without a reboot: while Maple was disabled, a private diagnostic-app copy of Maple was patched to the original system's `hhea/Typo/Win = 928/-244` metrics. Android changed the candidate's `ascent/descent` and baseline to exactly match the original-system face, and the QQ-shaped title layout contracted from 124 px to 111 px—the original-system result. Its `top/bottom` remained Maple's `-124/72`, proving that this Android path uses `ascent/descent` for layout, not the larger `top/bottom` values. The prior no-visible-improvement metric module result is therefore most plausibly explained by the original experiments not being selected by the affected process, rather than by Android ignoring the patched tables.

The staged complete 16-face module `maple-font-system-metrics.zip` was installed and rebooted successfully. It is mounted as `/system/fonts/MapleMono-NF-AllCJK-Regular.ttf`; its SHA-256 matches the staged module asset (`eb8addcd6b9575768f00dc9f51b004292087169542db9b4efdbaf9940b856406`), and the active QQ process (`com.tencent.mobileqq`, PID captured during validation) maps that exact system path. The diagnostic app reports the expected `ascent/descent = -88/23` and 111 px QQ-shaped title layout in the active system face, confirming the system-wide experiment is selected.

**Correction: do not treat this module as a QQ fix.** The owner rechecked the live page and reported that the header is still abnormal. The immediate re-capture confirms the QQ hierarchy is unchanged from the original Maple state: `title y=163..270` and `status y=270..290` inside the fixed `y=141..290` parent. The private-app metric experiment proves only that Android framework `TextView` layout responds to the patched tables; it does not prove that QQ's proprietary header layout reads or applies the same values. The system-metrics ZIP must remain an experiment, not a promotion candidate.

QQ maps the expected Regular, Medium, and Bold Maple files in its process, so this is not an asset-selection failure. A final-table `head` value is the remaining low-cost distinction: the current source font's real `head.yMax/yMin` are `1309/-761`, while the system-metrics experiment intentionally retained them. `patch_vertical_metrics.py` now supports paired `--head-y-max` / `--head-y-min` overrides, and the **Headbound** (`head-metrics`) workaround applies `hhea/Typo/Win/head = 928/-244` to all 16 faces. Its Regular audit confirms the table values but also confirms that hundreds of glyphs exceed this artificial head box; this candidate is a narrowly scoped QQ-renderer probe only, with significant clipping/metadata risk and no promotion path. Rebuild it only through `just mobile-headbound`; that recipe emits `font_module_dev/experiments/maple-font-headbound.zip` with a visibly unsafe module name.

The head-table probe was installed and verified on-device: `/system/fonts/MapleMono-NF-AllCJK-Regular.ttf` matches the active module asset SHA-256 (`bd106cb96e0108dd080a783f62b3b9c88e579f3d3f313599b4111637188afebb`), and the QQ process maps it. The owner reports the header visually restored. The captured QQ hierarchy confirms the decisive geometry change: nickname bounds shrink from `y=163..270` to `y=163..224`, and the status `ViewFlipper` moves from `y=270..290` to `y=224..260`, yielding a fully visible status line. The diagnostic app correspondingly reports the active face's `top/ascent/descent/bottom = -88/-88/23/24` for the title case. This demonstrates that QQ's layout path consults `head.yMax/yMin`, unlike the earlier Android framework-only experiment.

**Safety result:** do not promote this package as a general stable release. The same forged `head` range conflicts with real outlines (`glyph_y_max=1308.57`, `glyph_y_min=-750.89` in Regular; 415 glyphs above and 232 below the declared range). It proves the causal table but introduces metadata risk. The owner performed a smoke test across Settings, notifications, browser, QQ chat content, Chinese, accented Latin, descenders, mathematical symbols, and Emoji: no clipping or missing glyphs were observed, and normal use remains readable. However, paragraphs appear crowded, CJK glyphs look large, rare `〱` visibly intersects glyphs on adjacent lines, and some extreme paragraphs have adjacent-line overlap. Keep the head-metrics package strictly as an owner-accepted temporary workaround; a truthful outline-scaling candidate is recorded in `ROADMAP.md` as quality work, not an immediate blocker.

Evidence files: `qq-private-chat-maple.png`, `qq-private-chat-maple.xml`, `qq-private-chat-reference.png`, `qq-private-chat-reference.xml`, `qq-private-chat-system-metrics.png`, `qq-private-chat-system-metrics.xml`, `layout-diagnostic-qq-header-reference-with-maple.txt`, `layout-diagnostic-qq-header-system-metrics.txt`, `layout-diagnostic-system-metrics-module.txt`, `maple-regular-vertical-metrics.json`, and `sys-sans-hans-regular-vertical-metrics.json` under `font_module_dev/device_capture/`.

## Development roadmap

The complete staged roadmap, including Android layout diagnostics, configuration-drift detection, native explicit refresh, portable commands, optional KernelSU Next WebUI, font-content work, and release gates, is maintained in [ROADMAP.md](ROADMAP.md).

## 未完成 / 待下一任继续

1. **CJK Extension G–J 字形覆盖**：修改 locale 配置 ranges + 重新 CJK build
2. **模块体积缩减**：当前 16 个 full CJK 字体约 388.5 MiB（模块 ZIP 195.6 MiB）；可考虑选择性打包或 subset
3. **Native 自适应配置刷新器**：实现显式触发、解析 XML、fail-closed、保留 last-known-good 的设备端生成器；详细约束见 `report.md`
4. **Android 度量/布局诊断**：已完成原系统与 Maple 的初始 `Paint.FontMetricsInt` / 基线 / 布局边界对比，确认 QQ 实际使用 `head` bounds；Headbound 仅是 owner-accepted 临时 workaround，不能作为安全发行包。后续需做真实 outline geometry 候选。诊断 app 还可记录 shaping 后的实际字体路径，用于下一批 fallback 问题。
5. **通用 fallback 演进**：`maple-font-roboto-fallback` 已修复并实机验证 U+032B 组合附加符和所报颜文字，现已合入稳定构建和 Headbound 重建配方。后续改动需保持它是符号族之后的无语言标签 generic fallback，并重复四层 XML、命名空间、Play Store 和常规应用验证；不要将其与 CJK Extension G–J 重建或 CJK language family 改动混合。
6. **Play Store / Play Integrity Fork 兼容性**：根因已通过控制矩阵确认。PIF 的 Zygisk 代码对 `com.android.vending` 调用 `FORCE_DENYLIST_UNMOUNT`，移除 Maple overlay，但 FontManager 仍持有 Maple 路径，触发 Minikin 空指针崩溃。`manage.kernel_umount=false` 已在实机反证为无效。使用 Maple 系统字体时必须保持 PIF 禁用，或由 PIF / root-hiding 方案修复该强制卸载交互；完整证据见 `PLAY_STORE_DIAGNOSIS.md`。
7. **APatch 兼容性**：未测试
8. **magisk 专用安装器**：模块内 update-binary 仅为 Magisk 官方入口，未在 Magisk 实机测试
9. **CJK 静态资源 SHA-256 来源**：新增的 JP/TC/KR sha256 文件缺少来源说明和复验记录

### OpenType Collection（TTC）候选方案

由于模块覆盖四层字体配置，CJK fallback 可改为按 style 的多语言 TTC，而不必继续让每个 CJK language family 都引用同一份 AllCJK TTF。建议先创建一个仅用于 Regular 的四-face staging TTC，例如 `MapleMono-NF-CJK-Regular.ttc`，按固定 index 存放 CN、JP、TC、KR face；随后在四个 CJK language family 中引用同一 TTC，并使用 `index` 选择 locale face。原始 OxygenOS 配置已经使用带 index 的 `NotoSansCJK-Regular.ttc`，因此该 XML 表达方式与目标设备的既有模型一致。

- `zh-Hans` → TTC index `0`（CN）
- `ja` → TTC index `1`（JP）
- `zh-Hant,zh-Bopo` → TTC index `2`（TC）
- `ko` → TTC index `3`（KR）

仅四个 CJK language fallback family 应切换到 TTC；命名 UI family（`sans-serif`、`monospace` 等）保持当前单独的静态 Maple face。TTC 不应与原系统 Noto/SysSans face 混用。

潜在收益是语言隔离更清晰，并可能共享相同 OpenType 表而减少模块体积；实际节省取决于各 locale face 的表能否共享，不能假设按四倍线性缩减。实现需要使 `generate_configs.py` 的 font 节点生成支持 `index`，使 `build_module.py` 同步、校验 `.ttc` 资产，并提供确定性的 TTC 构建与 FontTools 校验。

在推广到 16 个 styles 前，必须先用 Regular staging 包实机验证：模块挂载、启动、语言切换、CJK fallback、Google App/普通 App 兼容性，以及 KernelSU Next 的“默认卸载模块”关闭要求。成功后再扩展到其余 style 并重新执行完整设备验证流程。

---

## Play Store crash root cause (resolved)

Google Play Store reproducibly crashes on this device when **Play Integrity Fork (PIF)** and a Maple system-font overlay are both enabled. The complete matrix is in [`PLAY_STORE_DIAGNOSIS.md`](PLAY_STORE_DIAGNOSIS.md).

**Summary:** PIF explicitly calls Zygisk's `FORCE_DENYLIST_UNMOUNT` option for Play Store. This removes the module-owned `/system/fonts` and font XML overlays from that app's mount namespace, while Android FontManager retains its previously resolved Maple `sans-serif` path. The missing file produces `SkData` failure and `Font::prepareFont()` null dereference.

**Rejected workaround:** `manage.kernel_umount=false` was installed in the active font module and tested with PIF enabled. It did not preserve Maple mounts or prevent the crash. The KernelSU `kernel_umount` feature was already disabled; this metadata does not override PIF's Zygisk forced unmount.

## 禁止事项（已通过实机验证应该避免）

> **新增 (2026-07-28):** 不要在此设备上同时启用 Play Integrity Fork 与 Maple 系统字体模块。除非 PIF 或 root-hiding stack 已经完成专门兼容性修复并通过应用命名空间验证，否则应保持 PIF 禁用。

- **不要在同一个 CJK language family 中混合 Maple 静态 face 与原始 Noto/SysSans face** — 会导致 bootloop
- **不要在模块中删除全局缓存**（/data/fonts, GMS, Gboard 等）— service.sh 和 uninstall.sh 已清理为只写诊断日志
- **不要开启 KernelSU "默认卸载模块"** — 系统字体模块必须对 App 进程可见

---

## 对下一任 Agent 的建议启动步骤

1. 阅读 `font_module_dev/ROADMAP.md` 确认当前阶段、依赖和验收条件
2. 阅读 `font_module_dev/report.md` 了解 OxygenOS 16 字体体系
3. 阅读 `font_module_dev/DEVICE_VALIDATION.md` 了解设备验证流程
4. 阅读本 HANDOFF.md
5. 检查 `git status --short` 确认当前工作区干净
6. 选择一个独立 workstream；不要并行混合 XML 刷新、字体几何、TTC 和 root-provider 兼容性改动
