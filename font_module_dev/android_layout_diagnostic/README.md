# Local Android Layout Diagnostics

This directory contains the Phase A1 diagnostic app from the module roadmap. It is intentionally a local-only, dependency-free Android project: it compares the active system `sans-serif` typeface with an explicitly loaded font file, renders fixed-height UI-like layouts, records `Paint.FontMetricsInt`, and emits a deterministic diagnostic report to Logcat.

## What it measures

- Active system `sans-serif` and an explicit candidate font path (default: `/system/fonts/MapleMono-NF-AllCJK-Regular.ttf`)
- `top`, `ascent`, `descent`, `bottom`, and `leading`
- fixed-height single-line, fixed-height multiline, title, list-row, chat, and button-like `TextView` layouts
- `includeFontPadding=true` and `false`
- automatic line height and explicit line height
- measured view bounds, text baseline, and visible text bounds relative to its containing view
- a fallback probe for the reported kaomoji code points, logging `Paint.hasGlyph()` for Batak letters, the combining inverted double arch below, and the Gurmukhi digit seven

The app uses Android framework APIs only. It has no network access, no storage permission, and does not alter any system configuration.

## Build

Run from the repository root in `cmd.exe`:

```bat
gradle -p font_module_dev\android_layout_diagnostic assembleDebug
```

The APK is written to `font_module_dev\android_layout_diagnostic\app\build\outputs\apk\debug\app-debug.apk`.

## Install and collect

The app runs its measurements immediately after it starts. Its report is logged with the `MapleLayoutDiagnostic` tag. The explicit-font path may be overridden with an Android activity extra.

```bat
adb install -r font_module_dev\android_layout_diagnostic\app\build\outputs\apk\debug\app-debug.apk
adb logcat -c
adb shell am start -n dev.maplefont.layoutdiagnostic/.MainActivity --es candidate_font /system/fonts/MapleMono-NF-AllCJK-Regular.ttf
adb logcat -d -s MapleLayoutDiagnostic:I > font_module_dev\device_capture\layout-diagnostic-maple.txt
adb exec-out screencap -p > font_module_dev\device_capture\layout-diagnostic-maple.png
```

For a reference run, reboot with the Maple module disabled, run the same collection command, and save it as `layout-diagnostic-reference.txt` / `layout-diagnostic-reference.png`. Comparing separate boots is intentional: the active system typeface is selected during Android startup and must be proven for each experiment.

If the explicit candidate path cannot be read by the app process, the app logs `candidate_load_failed` and continues measuring the active system typeface. Do not interpret candidate results unless the report records `candidate_load=success`.

## Report format

The app logs one line per case in a stable key/value form. Key measurements include `metrics_top`, `metrics_ascent`, `metrics_descent`, `metrics_bottom`, `metrics_leading`, `view_height`, `baseline`, `layout_top`, and `layout_bottom`. `layout_top` and `layout_bottom` are the Android text layout bounds relative to the `TextView` top; a negative `layout_top` or `layout_bottom > view_height` indicates layout extending beyond the view bounds.

Fallback records use `fallback_probe font=<system|candidate> codepoint=U+<hex> context=<isolated|with_underscore> has_glyph=<true|false> glyph_count=<n> glyph_fonts=<files>`. Combining marks are probed together with an underscore base, because an isolated combining mark does not represent the rendered kaomoji sequence. `Paint.hasGlyph()` reports whether Android can render the code point through the typeface's effective fallback collection; it does not prove that the selected font file's own cmap contains the code point. `glyph_fonts` is collected from Android's shaped glyph run and identifies the actual font files selected for that sample. Pair these records with the rendered `fallback_probe` sample, a screenshot, and a FontTools cmap audit when diagnosing a missing glyph.
