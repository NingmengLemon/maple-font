# Device Validation: CPH2747_16.0.9.400 (EX01)

Run every command from a host terminal with the phone connected. The collection commands are read-only. Do not install the module until the pre-install collection is saved.

## 1. Pre-install collection

```powershell
New-Item -ItemType Directory -Force .\font_module_dev\device_capture | Out-Null
adb shell su -c 'getprop ro.build.version.sdk; getprop ro.build.display.id; uname -a' | Out-File -Encoding utf8 .\font_module_dev\device_capture\identity.txt
adb shell 'su 0 sh -c "for d in /system/etc /system_ext/etc /product/etc /vendor/etc; do if [ -d \$d ]; then find \$d -maxdepth 1 -type f \( -name \"*font*.xml\" -o -name \"fonts.xml\" \) -print; fi; done"' | Out-File -Encoding utf8 .\font_module_dev\device_capture\font-config-paths.txt
adb shell 'su 0 sh -c "sha256sum /system/etc/font_fallback.xml /system/etc/fonts.xml /system_ext/etc/fonts_base.xml /system_ext/etc/fonts_ule.xml"' | Out-File -Encoding utf8 .\font_module_dev\device_capture\font-config-sha256.txt
adb exec-out su 0 cat /system/etc/font_fallback.xml > .\font_module_dev\device_capture\font_fallback.xml
adb exec-out su 0 cat /system/etc/fonts.xml > .\font_module_dev\device_capture\fonts.xml
adb exec-out su 0 cat /system_ext/etc/fonts_base.xml > .\font_module_dev\device_capture\fonts_base.xml
adb exec-out su 0 cat /system_ext/etc/fonts_ule.xml > .\font_module_dev\device_capture\fonts_ule.xml
adb shell 'su 0 sh -c "echo \"== modules ==\"; ls -la /data/adb/modules; echo \"== global module disable ==\"; ls -la /data/adb/modules/disable 2>/dev/null || true; echo \"== metamodule link ==\"; ls -la /data/adb/metamodule 2>/dev/null || true; echo \"== meta-overlayfs ==\"; ls -la /data/adb/modules/meta-overlayfs 2>/dev/null || true; echo \"== hybrid_mount ==\"; ls -la /data/adb/modules/hybrid_mount 2>/dev/null || true; echo \"== mount records ==\"; cat /proc/mounts | grep -E \"/system|modules|overlay\""' | Out-File -Encoding utf8 .\font_module_dev\device_capture\root-overlay-state.txt
adb shell su -c 'magisk -V 2>/dev/null; ksud --version 2>/dev/null; getprop | grep -E "^(\[ro\.build|\[ro\.oxygen|\[ro\.oplus)"' | Out-File -Encoding utf8 .\font_module_dev\device_capture\root-version.txt
```

Review `root-overlay-state.txt` before installation. A global `/data/adb/modules/disable` file disables every module; remove it only if intentional, then reboot before proceeding. When KernelSU / KernelSU Next is the root provider, verify a system-mount provider is active (for example the installed `hybrid_mount`, or a metamodule such as `meta-overlayfs`). This module does not install or configure that prerequisite.

For a system-font module, verify that normal application processes can see the mounted font files selected by Android's FontManager. If the files are absent from an application mount namespace while FontManager still resolves their paths, Minikin/HWUI can crash.

**⚠️ Confirmed Play Integrity Fork conflict on CPH2747:** the Play Integrity Fork Zygisk module explicitly requests `FORCE_DENYLIST_UNMOUNT` for processes whose data directory belongs to Google Play Services or Google Play Store. With Maple active, this removes the Maple font and XML overlays from `com.android.vending` while FontManager continues to resolve `sans-serif` to Maple paths. The result is the documented Minikin crash.

Do **not** enable Play Integrity Fork together with a Maple system-font overlay on this device profile. The KernelSU declaration `manage.kernel_umount=false` was tested in the active font module and did **not** prevent PIF/Zygisk Next from removing its overlay in Play Store. It is not a workaround for this interaction.

After every reboot, check the actual application namespace rather than inferring it from manager settings:
```sh
adb shell su -c 'p=$(pidof com.android.vending); find /proc/$p/root/system/fonts -maxdepth 1 -name "MapleMono-NF-AllCJK-*.ttf" | wc -l'
adb shell su -c 'p=$(pidof com.android.vending); grep /system/fonts /proc/$p/mountinfo'
adb shell su -c 'dumpsys font | grep MapleMono-NF-AllCJK-Medium.ttf | head -n 1'
```

A healthy Maple state has 16 Maple files and a KSU `/system/fonts` overlay in the Play Store namespace. See `PLAY_STORE_DIAGNOSIS.md` for the controlled test matrix and failure evidence.

## 2. Build and inspect the package

```powershell
uv run python .\merge_cjk_locales.py --dry
uv run python .\font_module_dev\build_module.py
Get-ChildItem .\font_module_dev\maple-font-module-v0.1.1-dev.zip
```

Install the ZIP with the active root manager application only. Do not flash it from recovery.

## 3. Post-install checks after one reboot

```powershell
adb wait-for-device
adb shell su -c 'cat /data/adb/modules/maple-font/module.prop; test -f /data/adb/modules/maple-font/disable && echo DISABLED || echo ENABLED'
adb shell 'su 0 sh -c "ls -l /system/fonts/MapleMono-NF-AllCJK-Regular.ttf /system/etc/font_fallback.xml /system/etc/fonts.xml /system_ext/etc/fonts_base.xml /system_ext/etc/fonts_ule.xml"'
adb shell 'su 0 sh -c "grep -n \"MapleMono-NF-AllCJK-Regular.ttf\" /system/etc/font_fallback.xml /system/etc/fonts.xml /system_ext/etc/fonts_base.xml /system_ext/etc/fonts_ule.xml"'
adb shell su -c 'cat /data/adb/modules/maple-font/service.log 2>/dev/null || true'
adb shell su -c 'logcat -d -b all -v brief | grep -iE "font|typeface" | tail -n 200'
```

Expected results:

- `/system/fonts/MapleMono-NF-AllCJK-Regular.ttf` exists after boot.
- Both overlaid XML files contain `MapleMono-NF-AllCJK-Regular.ttf`.
- The module is enabled and `service.log` reports 16 packaged Maple files.
- No framework font XML parse errors appear in the collected log.

If any expected result is absent, disable the module in the root manager or run `adb shell su -c 'touch /data/adb/modules/maple-font/disable'`, reboot, and keep the collected output for diagnosis.
