# Vertical-Metrics Experiments

This directory contains isolated module trees for the Android font-layout investigation. Every experiment copies the verified module XML and changes only the staged font data. None is a stable release artifact.

## Candidates

| Candidate | Table changes | Device result | Status |
| --- | --- | --- | --- |
| `ascent-970` | `hhea` and OS/2 `970/-300` | No visible QQ improvement. | Superseded. |
| `ascent-950` | `hhea` and OS/2 `950/-300` | No visible QQ improvement. | Superseded. |
| `system-metrics` | `hhea` and OS/2 `928/-244`, retaining actual `head` bounds | QQ still unchanged even though the process mapped the asset. | Superseded. |
| `head-metrics` (**Headbound**) | `hhea`, OS/2, and `head` all `928/-244` | QQ nickname/status header recovered. | Owner-accepted temporary workaround only. |

**Headbound** is the designated name for the `head-metrics` workaround. The name emphasizes that it constrains the OpenType `head` bounds rather than shrinking actual glyph outlines. The `head-metrics` directory remains the historical experiment identifier; use the `mobile-headbound` recipe to rebuild an installable package named `maple-font-headbound.zip`.

Headbound is deliberately unsafe as a general font design: many real Maple glyphs exceed its forged `head` range. It establishes that QQ consults `head.yMax/yMin`; it must not be promoted as a stable module without genuine outline scaling and truthful bounds.

## Layout

- `<candidate>/fonts/` is intentionally ignored by Git because it contains 16 large derived TTF files.
- `<candidate>/module/` is the installable module tree, retained for reproducibility and XML inspection.
- `<candidate>/regular-vertical-metrics.json` records a representative FontTools audit where available.
- `maple-font-*.zip` archives are local derived packages and are ignored by Git.

## Rebuild an experiment

Run from the repository root in `cmd.exe`:

```bat
just mobile-headbound
```

Use [`../device_capture/README.md`](../device_capture/README.md) for the on-device evidence and [`../ROADMAP.md`](../ROADMAP.md) for the future truthful-outline replacement plan.
