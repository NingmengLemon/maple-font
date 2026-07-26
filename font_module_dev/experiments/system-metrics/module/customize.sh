#!/system/bin/sh
# Maple Mono CJK font module installation customization.
#
# The platform installer extracts the module and supplies helper functions such
# as ui_print and set_perm_recursive. This file must not invoke those helpers
# at import time, because KernelSU and Magisk own the installation lifecycle.

SKIPUNZIP=0

ui_print "- Maple Mono NF AllCJK"
ui_print "- Target profile: OxygenOS 16 CPH2747_16.0.9.400 (EX01)"
ui_print "- Reboot after installation to apply the font overlay"
