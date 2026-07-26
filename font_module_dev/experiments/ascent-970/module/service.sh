#!/system/bin/sh
# Maple Mono module boot diagnostic. No system or application data is modified.

MODDIR=${0%/*}
LOG="$MODDIR/service.log"

log() {
    echo "[maple-font] $(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"
}

log "service start"
log "sdk=$(getprop ro.build.version.sdk) build=$(getprop ro.build.display.id)"
log "overlay fallback=$(test -f /system/etc/font_fallback.xml && echo present || echo missing)"
log "overlay fonts=$(test -f /system/etc/fonts.xml && echo present || echo missing)"
log "overlay fonts_base=$(test -f /system_ext/etc/fonts_base.xml && echo present || echo missing)"
log "overlay fonts_ule=$(test -f /system_ext/etc/fonts_ule.xml && echo present || echo missing)"
log "Maple files=$(find "$MODDIR/system/fonts" -type f -name 'MapleMono-NF-AllCJK-*.ttf' | wc -l)"
log "service complete"
