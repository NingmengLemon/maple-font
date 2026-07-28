# Play Store Minikin Crash Investigation

## Status

**Root cause confirmed for the tested device setup.** The crash is caused by Play Integrity Fork (PIF) requesting a Zygisk forced denylist unmount for Google Play Store, while Android's system FontManager has already resolved `sans-serif` to Maple overlay assets.

This is **not** evidence of an OpenType-table incompatibility in Maple, and the earlier claim that `manage.kernel_umount=false` resolves the problem is disproven by device testing.

## Scope

- Device: CPH2747, OxygenOS 16 / Android API 36.
- Affected package: `com.android.vending` (Google Play Store, version `52.4.41-34`).
- Root stack during verification: KernelSU Next 33223, hybrid_mount, Zygisk Next `1.4.3-817-e815170-release` with `enforce_denylist=2` (`just_umount`).
- Interaction module: Play Integrity Fork `v17`.
- Active font module during the final matrix: `maple-font-head-metrics`.

## Failure signature

The foreground Play Store process fails while measuring text:

```text
Font_File: open file nullptr
HWUI: Failed to make SkData from file name:
  /system/fonts/MapleMono-NF-AllCJK-Medium.ttf
SIGSEGV / null pointer dereference
minikin::Font::prepareFont()
minikin::Font::getExternalRefs()
minikin::FakedFont::typeface()
minikin::LayoutPiece::LayoutPiece()
```

The raw historical logcat captures are retained locally and intentionally excluded from version control because they can contain device-specific information. The controlled matrix and reproducible collection commands below preserve the evidence needed to revalidate this result.

## Earlier XML isolation results

The existing isolation packages established which FontManager selection path reaches the unavailable Maple asset:

| Module state | XML behavior | Result with the then-active root-module environment |
| --- | --- | --- |
| All Maple modules disabled | Original ROM XML and no Maple assets mounted | Play Store starts normally. |
| `maple-font` | All target UI and CJK families replaced | Minikin crash. |
| `maple-font-head-metrics` | Full Maple overlay with forged `head` bounds | Minikin crash. |
| `maple-font-preserve-cjk` | Maple named UI families, original CJK fallbacks | Minikin crash. |
| `maple-font-assets-only` | Maple assets mounted, original XML samples restored | No crash. |
| `maple-font-core-ui` | Only `sans-serif` and `monospace` replaced | Minikin crash. |
| `maple-font-sans-only` | Only `sans-serif` replaced | Minikin crash. |

Thus `sans-serif` is the sufficient **FontManager selection route** exercised by Play Store. It is not, by itself, proof that Maple font data or XML syntax is invalid: a process with the correct mount namespace can load the same files successfully.

## Controlled PIF interaction matrix

The following sequence used the same enabled Head Metrics overlay, hybrid_mount, and Zygisk Next `just_umount` policy. Each Play Store result was obtained after a reboot, a logcat clear, a forced stop, and a cold launch.

| Case | Play Integrity Fork | Font module `manage.kernel_umount=false` | Play Store font namespace | Result |
| --- | --- | --- | --- | --- |
| Baseline | Disabled | Absent in the originally installed Head Metrics module | 16 Maple TTFs and KSU overlays visible | Cold launch succeeds. |
| PIF interaction | Enabled | Absent | 0 Maple TTFs; no `/system/fonts`, `/system/etc`, or `/system_ext/etc` overlay entry | Minikin crash. |
| KernelSU metadata probe | Enabled | Present in the active Head Metrics module | 0 Maple TTFs; no font overlay entry | Same Minikin crash. |
| Recovery verification | Disabled | Present | 16 Maple TTFs and `/system/fonts` overlay visible | Play Store starts normally. |

During both metadata-probe states, KernelSU reported `kernel_umount` as disabled. The active module's `module.prop` nevertheless contained the candidate line `manage.kernel_umount=false`, while `ksud module config --internal maple-font-head-metrics list` reported no module configuration entries. The line did not alter the PIF-requested unmount.

## Confirmed root cause

Play Integrity Fork's upstream native module explicitly targets both Google Play Services and Play Store. In [`main.cpp`](https://github.com/osm0sis/PlayIntegrityFork/blob/main/app/src/main/cpp/main.cpp), its `preAppSpecialize()` method:

1. classifies a process whose app-data directory ends in `com.google.android.gms` or `com.android.vending` as a Google process;
2. calls `api->setOption(zygisk::FORCE_DENYLIST_UNMOUNT)` for every such process;
3. only then limits its property-spoofing payload to DroidGuard or Play Store.

Consequently, PIF explicitly asks the Zygisk implementation to strip module mounts from Play Store. Zygisk Next honors that request under the tested setup. The process then cannot open the Maple file selected earlier by FontManager, producing the observed null `SkData` and Minikin dereference.

The direct evidence is consistent across the matrix:

- FontManager, running in the system context, retains the Maple `sans-serif` path.
- With PIF enabled, the Play Store process contains zero `MapleMono-NF-AllCJK-*.ttf` files and no relevant KSU overlay mount.
- With PIF disabled, the same process can see all 16 faces and cold-starts normally, despite Zygisk Next remaining in `just_umount` mode.

## Rejected hypothesis: `manage.kernel_umount=false` in `module.prop`

KernelSU documents module feature management through the `ksud module config set manage.kernel_umount false` command. The candidate line added to Maple's `module.prop` did not create a KernelSU module configuration entry, and it did not affect the test outcome.

The final device probe installed an active font module that contained this exact `module.prop` line while PIF remained enabled. The crash and absent font mounts were unchanged. Do not add or describe this line as a Play Store crash fix, and do not rely on it to protect a systemless font overlay from PIF.

Even a correctly registered KernelSU automatic-unmount setting is not evidence that it overrides a Zygisk module's explicit `FORCE_DENYLIST_UNMOUNT` request. That separate interaction remains outside the font module's control.

## Safe operating state

For this device profile, keep Play Integrity Fork disabled whenever a Maple system-font overlay is enabled. This preserves Play Store startup and process-visible font assets.

Do not clear Play Store, Google Play Services, keyboard, font, or global caches as part of diagnosis.

## Follow-up options

1. **Compatibility-first:** keep PIF disabled while using Maple system fonts.
2. **PIF-side engineering:** maintain a separately built PIF variant that does not call `FORCE_DENYLIST_UNMOUNT` for `com.android.vending`, then independently validate Play Store behavior and Play Integrity verdicts. This changes PIF's root-hiding behavior and must not be presented as a no-risk font-module fix.
3. **Alternative root-hiding setup:** evaluate a root-hiding/Zygisk arrangement that preserves required systemless font mounts for Play Store. Validate it with the same namespace checks before relying on it.

Do not resume speculative Maple table, XML, or `sans-serif` changes until the root-provider interaction is held constant. The font module cannot make a file readable in a process from which PIF has deliberately removed its mount namespace.

## Reproducible evidence collection

After a cold launch, collect the following without modifying the device state:

```sh
adb shell pidof com.android.vending
adb shell su -c 'p=$(pidof com.android.vending); find /proc/$p/root/system/fonts -maxdepth 1 -name "MapleMono-NF-AllCJK-*.ttf" | wc -l'
adb shell su -c 'p=$(pidof com.android.vending); grep /system/fonts /proc/$p/mountinfo'
adb shell su -c 'dumpsys font | grep MapleMono-NF-AllCJK-Medium.ttf | head -n 1'
adb logcat -d -b crash -v threadtime
```

A healthy Maple/PIF-disabled state has 16 Maple faces and a KSU `/system/fonts` overlay in the Play Store namespace. The confirmed failure state has zero faces and no such overlay while `dumpsys font` still reports a Maple path.
