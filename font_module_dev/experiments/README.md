# Android Font Experiments

This directory contains isolated module trees for Android font-layout and fallback investigation. Every experiment derives from verified module XML and makes one scoped change. None is a stable release artifact.

## Candidates

| Candidate | Table changes | Device result | Status |
| --- | --- | --- | --- |
| `ascent-970` | `hhea` and OS/2 `970/-300` | No visible QQ improvement. | Superseded. |
| `ascent-950` | `hhea` and OS/2 `950/-300` | No visible QQ improvement. | Superseded. |
| `system-metrics` | `hhea` and OS/2 `928/-244`, retaining actual `head` bounds | QQ still unchanged even though the process mapped the asset. | Superseded. |
| `head-metrics` (**Headbound**) | `hhea`, OS/2, and `head` all `928/-244` | QQ nickname/status header recovered. | Owner-accepted temporary workaround only. |
| `roboto-fallback` | Adds existing system `Roboto-Regular.ttf` after generic Noto Symbols in all four XML overlays; no font asset is packaged. | U+032B kaomoji mark resolves through Roboto; no boot or Play Store regression observed. | Passed isolated fallback profile; not yet promoted to the stable module. |

**Headbound** is the designated name for the `head-metrics` workaround. The name emphasizes that it constrains the OpenType `head` bounds rather than shrinking actual glyph outlines. The `head-metrics` directory remains the historical experiment identifier; use the `mobile-headbound` recipe to rebuild an installable package named `maple-font-headbound.zip`.

Headbound is deliberately unsafe as a general font design: many real Maple glyphs exceed its forged `head` range. It establishes that QQ consults `head.yMax/yMin`; it must not be promoted as a stable module without genuine outline scaling and truthful bounds.

## Layout

- `<candidate>/fonts/` is intentionally ignored by Git because it contains 16 large derived TTF files.
- `<candidate>/module/` is the installable module tree, retained for reproducibility and XML inspection.
- `<candidate>/regular-vertical-metrics.json` records a representative FontTools audit where available.
- `maple-font-*.zip` archives are local derived packages and are ignored by Git.
- `roboto-fallback/module/` contains generated XML and module metadata, but its derived `system/fonts/` payload remains ignored. Recreate it with `python -m font_module_dev.package_experiment_module --help` and the `--generic-fallback-font Roboto-Regular.ttf` option.

## Rebuild an experiment

Run from the repository root in `cmd.exe`:

```bat
just mobile-headbound
```

Use [`../device_capture/README.md`](../device_capture/README.md) for the on-device evidence and [`../ROADMAP.md`](../ROADMAP.md) for the future truthful-outline replacement plan.
