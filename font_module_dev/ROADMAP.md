# Maple Mono OxygenOS 16 Module Roadmap

## Purpose and baseline

This roadmap evolves the verified OxygenOS 16 font-overlay module without weakening its boot safety. The target baseline is `CPH2747_16.0.9.400 (EX01)`, Android API 36, with KernelSU Next plus an enabled `hybrid_mount` provider.

The current stable module:

- installs 16 static `MapleMono-NF-AllCJK-*.ttf` faces;
- overlays four XML configurations under `system/etc` and `system_ext/etc`;
- replaces only the known UI families and four CJK language families;
- has completed boot, Zygisk, and application compatibility validation on the target profile.

Detailed evidence and configuration rules remain in [report.md](report.md), while current operational history is maintained in [HANDOFF.md](HANDOFF.md).

## Non-negotiable safety invariants

Every phase must preserve these properties:

1. Never write the physical `/system` or `/system_ext` partitions. All generated XML remains module-owned overlay content.
2. Never mix Maple static faces and original Noto/SysSans faces in the same CJK language family. That configuration bootlooped on the target device.
3. Do not clear global font, GMS, keyboard, or application caches.
4. Do not enable Play Integrity Fork together with a Maple system-font overlay on CPH2747 unless a PIF/root-hiding compatibility change has passed the Play Store namespace validation. PIF explicitly requests Zygisk forced unmount for Play Store; `manage.kernel_umount=false` does not override that request.
5. Treat unknown ROM configuration structures as unsupported and fail closed. Do not perform heuristic XML rewrites.
6. Preserve a last-known-good generated XML set before publishing a replacement.

## Workstream A: establish Android layout evidence

### Why this comes first

The final-font metrics experiment did not improve the reported application layout defect:

| Candidate | hhea/Typo/Win ascent/descent | Device result |
|---|---:|---|
| `ascent-970` | `970/-300` | No visible improvement |
| `ascent-950` | `950/-300` | No visible improvement |

The experiment modified only declared final TTF metrics; it did not modify actual CJK outlines or CJK source transforms. The next font-compatibility decision must be based on Android measurements, not inferred solely from OpenType tables.

### Phase A1: minimal Android diagnostic application

Build a small, local-only Android test application that loads an explicit original-system font and each Maple candidate. It must render representative Chinese, Latin, punctuation, and descender samples in:

- fixed-height single-line containers;
- fixed-height multiline containers;
- title, list-row, chat, and button-like layouts;
- `includeFontPadding = true` and `false` variants;
- automatic line height and explicit line-height variants.

For every test case, record `Paint.FontMetricsInt` (`top`, `ascent`, `descent`, `bottom`, `leading`), measured view bounds, baseline positions, and screenshots.

**Exit criteria:** the app proves which Android metrics and layout rules differ between the original and Maple fonts, and reproduces or rules out the affected-app failure mode.

### Phase A2: validate process-visible font selection

Before drawing conclusions from any candidate, confirm after reboot that the affected process sees the expected module font assets and XML overlay. Collect mounted paths, selected typeface/font logs when available, and a checksum of the candidate file as visible from the process context.

**Exit criteria:** every visual experiment has a recorded proof that the tested process selected the intended font file.

### Phase A3: source-level CJK geometry experiments

If the diagnostic application identifies baseline or ink-bound displacement, create isolated source builds that change CJK `y_scale` and `y_shift` conservatively. Do not promote a source candidate to the system module until its Android diagnostic output improves and real-app testing confirms the result.

**Current priority:** The validated QQ workaround uses a deliberately constrained `head.yMax/yMin` range. It restores the fixed header layout but does not shrink the actual CJK outlines. Consequently, some paragraph layouts remain visually crowded; rare tall characters such as `〱` can overlap glyphs on an adjacent line. Treat a true-outline candidate as quality work rather than a blocker: the current workaround is readable in the tested applications, but it is not a truthful-metrics final solution.

A source candidate must:

1. reduce CJK `y_scale` and/or adjust `y_shift` only in an isolated CJK source build;
2. scan both the complete glyph set and a UI-focused character set for real ink bounds;
3. set `head`, `hhea`, and OS/2 values from the resulting truthful geometry rather than forging a smaller `head` box;
4. compare QQ's private-chat header, paragraph line spacing, and `〱` adjacent-line behavior against the current workaround and original system font.

**Exit criteria:** at least one source-level candidate either measurably improves the reproduced layout without common-character clipping/overlap, or the geometry hypothesis is rejected with recorded evidence.

## Workstream B: adaptive module configuration lifecycle

### Desired lifecycle

The module should eventually adapt to ROM font-configuration changes without attempting to regenerate XML during boot:

```text
install or explicit refresh
  -> inspect verified underlying ROM XML
  -> generate + validate staging overlays
  -> atomically publish module-owned XML and metadata
  -> user reboots
next boot
  -> normal module mount exposes pre-generated XML
  -> Android loads the overlay during early startup
```

`service.sh` must never perform a current-boot XML rewrite or remount operation. It may only detect configuration drift, persist state, and notify the user.

### Phase B1: configuration identity and deprecated-state detection

At installation or successful refresh, save a machine-readable state record containing:

- `ro.build.fingerprint`;
- `ro.build.version.incremental`;
- `ro.build.display.id`;
- hashes and source metadata for each of the four XML inputs;
- generated-overlay hashes, generation time, and module version.

At every boot, `service.sh` compares the live build identity with the recorded identity. If it differs, it marks the overlay state as `deprecated` and logs the reason. It must not modify the current XML or fonts.

A build-identity mismatch is a low-cost indication of a possible OTA. It is not proof that XML changed; it tells the user to run explicit validation or refresh.

**Exit criteria:** an identity mismatch after a test OTA or simulated changed state produces a durable, human-readable `deprecated` status while the previous known-good overlay remains active.

### Phase B2: native XML transformer

Bundle a statically linked native tool under a future `module/bin/<abi>/` path. Rust or C/C++ are acceptable. The tool must use a real XML parser and support:

- `refresh`: read verified lower-ROM sources, transform target families, stage output, validate, back up the current known-good set, and atomically publish;
- `validate`: verify current state and XML/assets without changes;
- `rollback`: restore the previous known-good XML set.

The transformer must reproduce the conservative semantics of [generate_configs.py](generate_configs.py):

- replace required `sans-serif` and `monospace` families;
- replace optional recognized UI families only when present;
- replace exactly the four recognized CJK language families;
- preserve all unrelated nodes and ordering;
- reject an unexpected root element, incomplete CJK replacement, invalid XML, missing Maple assets, or same-language Maple/Noto mixing.

The supported ABI set must be declared explicitly. The initial target may be `arm64-v8a`; unsupported ABIs fail closed.

**Exit criteria:** fixture tests show equivalent output semantics to [generate_configs.py](generate_configs.py), failure paths leave the active overlay untouched, and an on-device refresh followed by reboot passes the existing device validation flow.

### Phase B3: source-of-truth hardening

A refresh must not mistake its own mounted overlay for an original ROM configuration. Prefer installation-time source snapshots plus hashes, then verify a lower-partition view when the root provider makes that possible. If the tool cannot prove that input is an underlying-ROM XML file, it must refuse to regenerate and retain the existing configuration.

**Exit criteria:** refresh rejects module-owned overlay input and succeeds only when all four sources pass provenance checks.

## Workstream C: user-triggered management surfaces

### Phase C1: portable command entry point

Provide a module-local launcher and an optional `action.sh` path for managers that support module actions. The launcher exposes fixed subcommands only: `status`, `validate`, `refresh`, and `rollback`. It must not accept arbitrary user text that can reach a root shell.

This command path is the mandatory baseline for Magisk, KernelSU variants without WebUI support, and adb/shell maintenance.

**Exit criteria:** every state transition is usable and logged without a WebUI.

### Phase C2: KernelSU Next WebUI

KernelSU Next's current implementation recognizes a module `webroot` directory under `/data/adb/modules/<id>/` and serves it in its WebUI. Its JavaScript bridge provides `moduleInfo()`, root `exec`/`spawn`, and `toast()` APIs. The implementation and API references checked during planning are:

- [KernelSU Next WebUI activity](https://github.com/KernelSU-Next/KernelSU-Next/blob/dev/manager/app/src/main/java/com/rifsxd/ksunext/ui/webui/WebUIActivity.kt)
- [KernelSU Next WebUI API documentation](https://github.com/KernelSU-Next/KernelSU-Next/blob/dev/docs/WebUi_Next/API_DOC.md)
- [KernelSU Next module constants](https://github.com/KernelSU-Next/KernelSU-Next/blob/dev/userspace/ksud/src/defs.rs)

The optional WebUI should show:

- current ROM identity and the identity used by the active generated overlay;
- `current`, `deprecated`, `refresh-failed`, and rollback-available states;
- generated XML hashes, timestamps, and the last diagnostic error;
- buttons for `validate`, `refresh`, and `rollback`.

The WebUI must invoke only fixed module-local launcher commands. It does not edit XML directly and must always show that a successful refresh requires reboot.

**Exit criteria:** on a supported KernelSU Next Manager, the WebUI reports state accurately, invokes the same launcher as C1, handles errors, and never permits arbitrary shell command entry.

## Verified compatibility experiment: generic fallback

The `maple-font-roboto-fallback` staging module has passed a targeted CPH2747 validation. It inserts the existing system `Roboto-Regular.ttf` after the generic Noto Symbols family in all four overlays; it does not alter named Maple families, package Roboto, or mix original faces into the four CJK language families.

The test resolves the reported kaomoji's U+032B combining mark. Android shaping selects Roboto for the underscore-plus-U+032B sequence, preserves Maple for U+0325, and preserves the existing Batak/Gurmukhi fallbacks for the remaining non-CJK characters. Live XML, `dumpsys font`, the Play Store mount namespace, visual rendering, and font-error checks all passed with PIF disabled.

The opt-in generic fallback must remain an explicit, independently validated configuration profile until it has passed the full release matrix. It is not a substitute for source-built CJK Extension G–J coverage, and it must not be combined with CJK-family edits. See [FALLBACK_DIAGNOSIS.md](FALLBACK_DIAGNOSIS.md) for the evidence.

## Workstream D: font content and package evolution

### Phase D1: CJK Extension G through J coverage

Add verified supplementary-plane ranges to the locale configurations, rebuild CJK output, merge all locales, audit coverage, and validate a staged module. This is a source range/build task, not an XML fallback task.

**Exit criteria:** audit reports the expected mapped codepoints for supported source outlines, and a staged module boots without adding unsafe Noto fallback families.

### Phase D2: package-size and locale architecture

Evaluate the proposed locale-indexed TTC design with one Regular staging package before changing all styles. Measure actual package-size savings, language fallback correctness, and app compatibility. Do not assume shared OpenType tables produce linear savings.

**Exit criteria:** the Regular TTC staging module passes boot, language switching, fallback, and application checks; only then consider full-style rollout.

### Phase D3: broader compatibility

Validate Magisk and APatch independently. Do not infer support from the current KernelSU Next plus `hybrid_mount` evidence.

**Exit criteria:** each provider has a documented install, mount, reboot, fallback, and rollback validation record.

## Delivery order

1. Finish Workstream A before making more speculative font-metric patches.
2. Implement B1 drift detection; it is low-risk and immediately useful after OTAs.
3. Implement C1 portable commands, then B2/B3 native refresh with fixture-first tests.
4. Add C2 WebUI only after the command path is proven; WebUI remains an optional KernelSU Next enhancement.
5. Promote the verified generic fallback only through a separately reviewed profile after its full application matrix passes; keep it independent from CJK source and TTC work.
6. Pursue D1/D2/D3 as separately staged font/package compatibility work.

## Release gate

A release that includes adaptive refresh must demonstrate all of the following:

- existing boot safety invariants remain satisfied;
- a successful refresh survives reboot and activates the intended XML;
- a failed refresh leaves the prior overlay intact;
- deprecated state is visible without modifying XML at boot;
- rollback restores a previously validated state;
- the portable command path works without WebUI;
- KernelSU Next WebUI, if included, is optional and cannot execute arbitrary commands.
