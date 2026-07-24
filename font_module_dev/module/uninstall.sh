#!/system/bin/sh
# The manager removes the module directory and its systemless overlay.
# Do not delete global font or application caches here.

MODDIR=${0%/*}
rm -f "$MODDIR/service.log"
