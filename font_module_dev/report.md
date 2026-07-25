# OxygenOS 16 CPH2747 Font Configuration Notes

## Scope and evidence

This document is specific to the sampled device build:

- Device build: `CPH2747_16.0.9.400 (EX01)`.
- Android API level: 36 (Android 16).
- Kernel reported by the owner: `6.12.23-android16`.
- Pulled configuration samples: [`samples/font_fallback.xml`](samples/font_fallback.xml), [`samples/fonts.xml`](samples/fonts.xml), [`samples/fonts_base.xml`](samples/fonts_base.xml), and [`samples/fonts_ule.xml`](samples/fonts_ule.xml).
- The owner's rooted-device listing confirms that the referenced Android, OPlus, Noto, Roboto, and SysSans font files are physically present under `/system/fonts`.

The following paths were explicitly absent on this build at the time of inspection:

- `/system/etc/fonts_base.xml`
- `/system/etc/fonts_slate.xml`
- `/product/fonts`

A path-complete collection also found two active system-ext configurations that the initial collection missed:

- [`samples/fonts_base.xml`](samples/fonts_base.xml) from `/system_ext/etc/fonts_base.xml`
- [`samples/fonts_ule.xml`](samples/fonts_ule.xml) from `/system_ext/etc/fonts_ule.xml`

Both include named UI families and CJK fallbacks, so they are now overlaid alongside the two `/system/etc` files. Other OxygenOS builds may differ, so every new build must be sampled again.

## Observed configuration model

### `font_fallback.xml`

[`samples/font_fallback.xml`](samples/font_fallback.xml) defines the active Android-style family set: named families, aliases, script/language fallbacks, and emoji fallbacks. It includes named `sans-serif`, `monospace`, `roboto`, and `roboto-flex` families. Its CJK families are explicitly associated with `zh-Hans`, `zh-Hant,zh-Bopo`, `ja`, and `ko`.

The CJK fallback sources in the sampled file are:

| Language selector | Original source |
|---|---|
| `zh-Hans` | face index 2 of `NotoSansCJK-Regular.ttc` |
| `zh-Hant,zh-Bopo` | face index 3 of `NotoSansCJK-Regular.ttc` |
| `ja` | face index 0 of `NotoSansCJK-Regular.ttc` |
| `ko` | face index 1 of `NotoSansCJK-Regular.ttc` |

The file places general-script fallbacks and the CJK families before emoji/symbol fallback entries. Preserving the relative order of families not deliberately changed is important because Android resolves fallback candidates in order.

### `fonts.xml`

[`samples/fonts.xml`](samples/fonts.xml) begins with an Android deprecation notice: system font configuration is no longer sourced from this file, while third-party parsers may still read it. The same sample nevertheless contains OxygenOS-specific named families:

- `sys-sans-en` → `SysSans-En-Regular.ttf`
- `op-sans-en` → `OPSans-En-Regular.ttf`
- `osans-solid-digits` → `OSans-Solid-Digits-VF.ttf`
- `sans-serif` → `SysFont-Regular.ttf`
- CJK fallback → `SysSans-Hans-Regular.ttf`, `SysSans-Hant-Regular.ttf`, and the Noto CJK collection

The module therefore overlays both files: `font_fallback.xml` for the platform configuration and `fonts.xml` only to maintain a matching view for legacy consumers. The second overlay is compatibility work, not evidence that Android 16 loads it as the canonical configuration.

## Replacement design

[`generate_configs.py`](generate_configs.py) builds module configurations directly from the four pulled samples. It only replaces these families:

1. Required named families: `sans-serif` and `monospace`.
2. Optional named families if present: `roboto`, `roboto-flex`, `sans-serif-condensed`, `sys-sans-en`, and `op-sans-en`.
3. The four CJK families that actually contain `NotoSansCJK`, `SysSans-Hans`, or `SysSans-Hant` files.

Everything else—including Arabic, Indic, Thai, Myanmar, Tibetan, symbols, emoji, OPlus special-purpose families, aliases, and the fallback ordering—is retained from the pulled XML. This is intentionally more conservative than replacing an entire hand-written font configuration.

The generated files live at:

- [`module/system/etc/font_fallback.xml`](module/system/etc/font_fallback.xml)
- [`module/system/etc/fonts.xml`](module/system/etc/fonts.xml)

The second collection also established that the system-ext profiles take part in the same family/fallback scheme:

- [`samples/fonts_base.xml`](samples/fonts_base.xml) contains `sans-serif`, `sys-sans-en`, `op-sans-en`, `monospace`, `roboto-flex`, and CJK fallback families.
- [`samples/fonts_ule.xml`](samples/fonts_ule.xml) contains `sans-serif`, OPlus English families, `monospace`, and CJK fallback families; it does not define `roboto-flex`, so the generator treats that family as optional per input file.

[`generate_configs.py`](generate_configs.py) now emits all four matched overlays under their original partitions:

- [`module/system/etc/font_fallback.xml`](module/system/etc/font_fallback.xml)
- [`module/system/etc/fonts.xml`](module/system/etc/fonts.xml)
- [`module/system_ext/etc/fonts_base.xml`](module/system_ext/etc/fonts_base.xml)
- [`module/system_ext/etc/fonts_ule.xml`](module/system_ext/etc/fonts_ule.xml)

They reference only the exact merged output names produced by [`merge_cjk_locales.py`](../merge_cjk_locales.py): `MapleMono-NF-AllCJK-*.ttf`.

## CJK merge semantics and coverage boundary

[`merge_cjk_locales.py`](../merge_cjk_locales.py) receives locales in priority order. The default is `CN,JP,TC,KR`, so the first available glyph mapping wins on conflicts. The merge script defaults to fail-closed: if any selected input style or locale is missing, it exits rather than emitting a misleading `AllCJK` output. `--allow-missing` is an explicit escape hatch for development only.

The current locale configuration deliberately ends at `U+FFEF`; for example, [`config-cn.json`](../source/cjk/cn/config-cn.json) includes the BMP CJK ranges but no supplementary-plane CJK ranges. Consequently the generated Maple fonts contain **zero** mappings for CJK Extensions G (`U+30000`), H (`U+31350`), I (`U+2EBF0`), and J (`U+323B0`). This is a source-coverage limitation, not an error introduced by locale priority merging.

Do not add a second same-language fallback family after Maple on this device without a dedicated framework-level validation: that experiment caused a boot loop on CPH2747 during real-device testing and has been reverted. The current boot-proven profile therefore intentionally replaces each original CJK family with Maple only.

That leaves Extensions G–J unresolved in the current profile. A future enhancement must use a source font that actually contains those outlines, explicitly add the relevant supplementary-plane ranges to each locale configuration, and validate a minimal staged profile before it can safely replace the existing all-CJK module.

A unit test in [`test_cjk_locale_merge.py`](../scripts/tests/test_cjk_locale_merge.py) verifies that a codepoint collision keeps the base locale mapping while non-conflicting codepoints from later locales are added.

## Module compatibility and installation boundary

The built package is generated by [`build_module.py`](build_module.py). It regenerates the XML from the pulled samples, copies the merged Maple files, verifies every Maple reference, and packages the standard Magisk module installer entrypoint.

- **Magisk:** The ZIP is intended for installation through the Magisk app. Its `META-INF` installer is the current minimal Magisk entrypoint that loads Magisk's own `util_functions.sh`; it does not contain a project-maintained extraction or mount implementation.
- **KernelSU / KernelSU Next:** The device has an active `hybrid_mount` metamodule: [`/data/adb/metamodule`](device_capture/root-overlay-state.txt) points to it, and its configuration uses `mountsource = "KSU"`, `default_mode = "overlay"`, and `overlay_mode = "ext4"`. Existing KSU overlays are visible in [`system-font-mount-state.txt`](device_capture/system-font-mount-state.txt). This establishes that the required mount provider is installed and operating. The module itself still does not modify that global provider configuration.
- **APatch:** Not validated. No compatibility claim is made.

The module boot script [`module/service.sh`](module/service.sh) writes only diagnostic state to its own module directory. It never removes font, GMS, Gboard, or application caches. Uninstallation also does not delete global caches.

## Proposed adaptive configuration refresh

### Scope

The next module-generation direction is an **explicit, native configuration refresh** command. It is not a boot-time XML rewrite. A user invokes refresh after an OTA or when moving the module to a device with a newly inspected font configuration; the command produces module-owned overlays, and the user reboots for Android to load them during normal early boot.

A boot-time implementation is deliberately out of scope: [`module/service.sh`](module/service.sh) runs after Android has normally loaded its font configuration, while the active systemless mount layout is established before module scripts run. Rewriting module files at that point cannot reliably affect the current boot and must not attempt manual remounts that compete with `hybrid_mount`.

### Native generator design

Bundle a small, statically linked native executable under a future `module/bin/<abi>/` directory. Rust or C/C++ are both suitable, provided the executable uses an actual XML parser and has no runtime library dependencies beyond Android's base environment.

The tool should implement `refresh`, `validate`, and `rollback` operations:

1. `refresh` reads a verified underlying-ROM XML source for the four known paths, transforms only the existing target families, writes staging files under the module directory, validates the full staged set, then atomically publishes it as the next boot's overlay.
2. `validate` parses the current module-owned XML and checks its structural and asset invariants without changing it.
3. `rollback` restores the previous last-known-good XML set retained by the preceding successful refresh.

The native transformation must retain the conservative semantics of [`generate_configs.py`](generate_configs.py): replace required `sans-serif` and `monospace` families, replace optional known UI families when present, replace exactly the four recognized CJK language families, preserve all other nodes and their relative ordering, and never append a same-language Noto/SysSans fallback behind Maple.

### Safety and source-of-truth rules

- Never write to physical `/system` or `/system_ext`; only publish under the module's own overlay tree.
- Do not parse an already-overlaid module file as if it were the underlying ROM source. Installation should save source snapshots and their hashes; refresh should use a verified lower-partition view or fail closed when it cannot distinguish the lower file from the module overlay.
- Keep the known path set explicit: `/system/etc/font_fallback.xml`, `/system/etc/fonts.xml`, `/system_ext/etc/fonts_base.xml`, and `/system_ext/etc/fonts_ule.xml`. Unknown locations require a separately validated device profile, not heuristic replacement.
- Require XML parse success, exact CJK-family replacement count, valid Maple asset references, and no Maple/Noto mixed same-language family before publication.
- Publish with temporary files plus atomic rename and retain a `last-known-good` copy. A failed refresh must leave the current overlays untouched and emit a diagnostic log.
- Fail closed on unsupported ABI, unavailable source XML, unknown structure, or incomplete module font assets.

### Verification plan

First validate the native transformer against the checked-in samples: it must produce equivalent XML semantics to [`generate_configs.py`](generate_configs.py). Then test on-device only as an explicit command: snapshot the underlying files, refresh, inspect generated XML and module assets, reboot, and run the existing post-install checks. Do not move generation into [`module/service.sh`](module/service.sh) unless a separate early-mount design is proven on the target root provider.

## Required on-device verification

Before installing, collect the output from the commands in [`DEVICE_VALIDATION.md`](DEVICE_VALIDATION.md). After installing and rebooting, collect its post-install section as well. The test must confirm both that the systemless files are mounted and that Android accepts the replacement XML; a successful ZIP installation alone is insufficient.

## External references

- Android custom font fallback documentation: <https://source.android.com/docs/core/fonts/custom-font-fallback>
- Magisk developer guide: <https://topjohnwu.github.io/Magisk/guides.html>
- KernelSU module guide: <https://kernelsu.org/guide/module.html>
- Reference CJK module template (historical; do not copy its assumptions blindly): <https://github.com/lxgw/advanced-cjk-font-magisk-module-template>
