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

### 已实机验证能正常启动、Zygisk 正常、App 兼容的配置：

- **字体文件：** `fonts/NF-AllCJK/MapleMono-NF-AllCJK-*.ttf`（16 个静态 face）
- **XML 覆盖：** 四层 overlay（system/etc × 2 + system_ext/etc × 2）
  - `system/etc/font_fallback.xml`
  - `system/etc/fonts.xml`
  - `system_ext/etc/fonts_base.xml`
  - `system_ext/etc/fonts_ule.xml`
- **XML 生成器：** `generate_configs.py` — 从实机 samples/ 生成 overlay
  - CJK family 仅替换为 Maple 静态 face，不拼接 Noto fallback
- **构建器：** `build_module.py` — 再生 XML → 复制字体 → 校验引用 → 打包 ZIP
  - ZIP 输出：`font_module_dev/maple-font-module-v0.1.0-dev.zip`（~195.6 MiB）

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

## 关键文件路径与用途

| 路径 | 用途 | 来源 |
|------|------|------|
| `merge_cjk_locales.py` | CJK locale 优先级合并脚本 | 上一任 |
| `font_module_dev/generate_configs.py` | 从实机 samples 生成模块 XML | 新写 |
| `font_module_dev/build_module.py` | 构建模块 ZIP + 校验 | 重构 |
| `scripts/tests/test_cjk_locale_merge.py` | merge 优先级 + 配置生成单测 | 新写 |
| `font_module_dev/audit_cjk_extensions.py` | 只读审计源字体 Extended 区覆盖 | 新写 |
| `font_module_dev/module/system/etc/*.xml` | 生成的 system overlay | generate_configs → build_module |
| `font_module_dev/module/system_ext/etc/*.xml` | 生成的 system_ext overlay | generate_configs → build_module |
| `font_module_dev/samples/*.xml` | 从实机拉取的原始配置样本 | 实机 adb pull + exec-out |
| `font_module_dev/device_capture/` | 所有设备诊断捕获 | 实机 adb 只读命令 |
| `font_module_dev/report.md` | 调研报告 | 维护中 |
| `font_module_dev/DEVICE_VALIDATION.md` | 设备验证命令集合 | 维护中 |
| `font_module_dev/maple-font-module-v0.1.0-dev.zip` | 构建产物 | build_module.py |

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

---

## 未完成 / 待下一任继续

1. **CJK Extension G–J 字形覆盖**：修改 locale 配置 ranges + 重新 CJK build
2. **模块体积缩减**：当前 16 个 full CJK 字体约 388.5 MiB（模块 ZIP 195.6 MiB）；可考虑选择性打包或 subset
3. **APatch 兼容性**：未测试
4. **magisk 专用安装器**：模块内 update-binary 仅为 Magisk 官方入口，未在 Magisk 实机测试
5. **CJK 静态资源 SHA-256 来源**：新增的 JP/TC/KR sha256 文件缺少来源说明和复验记录

---

## 禁止事项（已通过实机验证应该避免）

- **不要在同一个 CJK language family 中混合 Maple 静态 face 与原始 Noto/SysSans face** — 会导致 bootloop
- **不要在模块中删除全局缓存**（/data/fonts, GMS, Gboard 等）— service.sh 和 uninstall.sh 已清理为只写诊断日志
- **不要开启 KernelSU "默认卸载模块"** — 系统字体模块必须对 App 进程可见

---

## 对下一任 Agent 的建议启动步骤

1. 阅读 `font_module_dev/report.md` 了解 OxygenOS 16 字体体系
2. 阅读 `font_module_dev/DEVICE_VALIDATION.md` 了解设备验证流程
3. 阅读本 HANDOFF.md
4. 检查 `git status --short` 确认当前工作区干净
5. 决定下一步是解决 Ext G–J 字形、增量改进模块、还是发布打包
