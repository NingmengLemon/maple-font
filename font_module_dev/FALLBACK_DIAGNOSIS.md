# Android 16 Fallback Diagnosis

## Scope and result

This note records the first investigation of the reported kaomoji:

```text
喵ᯠ  _   ̫  _ ̥ ᯄ ੭
```

The target remains CPH2747 on OxygenOS 16 / API 36 with the currently active Maple module. The problem is not a single CJK coverage issue. The string contains Batak letters, a combining mark, and a Gurmukhi digit:

| Code point | Unicode name | Maple AllCJK Regular cmap | Active system supplier | Effective probe result |
| --- | --- | --- | --- | --- |
| U+1BE0 | Batak Letter Nya | absent | Noto Sans Batak | resolved by shaping |
| U+032B | Combining Inverted Double Arch Below | absent | Roboto | resolved by shaping |
| U+0325 | Combining Ring Below | present | Maple | resolved by shaping |
| U+1BC4 | Batak Letter Mandailing Ha | absent | Noto Sans Batak | resolved by shaping |
| U+0A6D | Gurmukhi Digit Seven | absent | Noto Sans Gurmukhi | resolved by shaping |

The corresponding application run is retained in the ignored device-capture directory. `Paint.hasGlyph()` remains `false` for the underscore-plus-combining-mark probes, but this API is not a reliable per-code-point test for a multiple-glyph sequence. The shaped glyph run is decisive: both U+032B and its underscore are selected from `Roboto-Regular.ttf`; the U+0325 sequence is selected from Maple. This matches the owner’s visible result after reboot: the complete kaomoji now renders normally.

## Android 16 configuration model

Android 15 and later use `font_fallback.xml` for new variable-font and fallback configuration; `fonts.xml` is deprecated for canonical platform configuration. The AOSP documentation is available at <https://source.android.com/docs/core/fonts/custom-font-fallback>.

On this OxygenOS build, the boot-proven module overlays four configuration files. The active system font dump confirms that it registers the preserved Batak fallback and the preserved Gurmukhi fallback, while the named Maple faces remain the selected `sans-serif` family. The replacement generator intentionally retains every non-target fallback family, so this behavior is expected from [`generate_configs.py`](generate_configs.py:1).

Minikin selects a fallback using coverage before locale and variant. Its current implementation is available at <https://android.googlesource.com/platform/frameworks/minikin/+/refs/heads/main/libs/minikin/FontCollection.cpp>; the score order means a generic fallback only participates when the Maple primary family has no glyph for that code point. Therefore, adding a narrowly scoped generic fallback does not cause it to replace glyphs that Maple already covers.

## Why no tofu is visible

U+032B is a nonspacing combining mark. A missing combining mark can disappear rather than producing an independently positioned tofu box, especially in a sequence such as an underscore followed by the mark. Consequently, the absence of a tofu box is not proof that the glyph was found.

The app's [`logFallbackProbe()`](android_layout_diagnostic/app/src/main/java/dev/maplefont/layoutdiagnostic/MainActivity.java:222) now exercises the actual reported sequence, logs `Paint.hasGlyph()`, and inspects the font file used for every shaped glyph through [`TextRunShaper.shapeTextRun()`](android_layout_diagnostic/app/src/main/java/dev/maplefont/layoutdiagnostic/MainActivity.java:225). It also renders the complete string. The [`README.md`](android_layout_diagnostic/README.md:1) explains why combining sequences require a shaped-run and visible-output check rather than interpreting `hasGlyph=false` alone as a failure.

## Confirmed local evidence

A FontTools cmap audit established the following:

- Maple Regular contains U+0325 but not U+1BE0, U+032B, U+1BC4, or U+0A6D.
- The device's `NotoSansBatak-Regular.ttf` supplies U+1BE0 and U+1BC4.
- The device's `NotoSansGurmukhi-VF.ttf` supplies U+0A6D.
- The device's `Roboto-Regular.ttf` contains U+032B and U+0325, but the current fallback collection does not select it for the underscore-plus-U+032B sequence.
- `dumpsys font` registers the Batak family as `und-Batk` and the Gurmukhi family as `und-Guru`; both are still present after the Maple overlay.

This distinguishes the single confirmed fallback hole from the separate Extension G through J issue. Extension coverage remains a CJK source-range rebuild task; it must not be conflated with the generic combining-mark fallback.

## Prepared isolated experiment

Do not alter the stable module or mix original Noto/SysSans faces into any of the four CJK language families. That configuration is known to bootloop on this device.

A separately named staging package was first built at `font_module_dev/experiments/maple-font-roboto-fallback.zip`. It changes only the four generated XML files by adding one generic fallback entry for the already installed `Roboto-Regular.ttf`, positioned after the preserved generic symbol fallback. It does not package a Roboto asset, change a named Maple family, or modify any CJK language family. The owner installed it through the root manager and rebooted successfully.

After that targeted device validation, the stable [`build_module.py`](build_module.py:1) build now regenerates all four overlays with the same `Roboto-Regular.ttf` generic fallback. [`package_experiment_module.py`](package_experiment_module.py:28) retains the `--generic-fallback-font` switch for independently staged profiles such as Headbound. Fixture coverage in [`test_cjk_locale_merge.py`](../scripts/tests/test_cjk_locale_merge.py:156) verifies that the insertion occurs after the generic Noto Symbols family even when aliases are interspersed between `family` elements.

Both the staging package and the stable build XML are checked to contain exactly one adjacent Noto Symbols → Roboto generic fallback pair in each of the four overlays, with no Roboto file under the module's `system/fonts` directory. The module still packages exactly the 16 Maple faces.

The purpose is only to make Roboto eligible when no earlier fallback covers U+032B. Maple remains primary for every code point it maps, and Noto Symbols remains earlier for its own coverage. This is the smallest evidence-based way to test the missing combining mark.

### Required validation

1. Keep Play Integrity Fork disabled and retain the known-good root mount configuration.
2. Install the staging module through the root manager and reboot once.
3. Verify all four XML overlays and the intended generic Roboto fallback in the live filesystem and in `dumpsys font`.
4. Run the fallback diagnostic and confirm that U+032B in `with_underscore` context becomes resolvable.
5. Capture a screenshot of the full kaomoji and inspect the combining-mark placement.
6. Repeat the existing boot, Settings, QQ, and Play Store checks. Do not clear application or global font caches.
7. Disable the staging module and reboot immediately if XML parsing, ordinary text fallback, or application startup regresses.

### On-device result

The live device confirmed all four module overlays, the generic Noto Symbols → Roboto pair, the existing Maple assets, and a `dumpsys font` Roboto entry. The shaped diagnostic result is:

- U+1BE0 and U+1BC4: `NotoSansBatak-Regular.ttf`.
- U+0A6D: `NotoSansGurmukhi-VF.ttf`.
- U+032B with underscore: both glyphs use `Roboto-Regular.ttf`.
- U+0325 with underscore: both glyphs use `MapleMono-NF-AllCJK-Regular.ttf`.

The owner verified that the original kaomoji looks normal. This is a passing result for the narrow generic-fallback fix, which is now included in the regular module build. The CJK Extension G through J rebuild and the truthful CJK-outline metrics work remain independent workstreams.
