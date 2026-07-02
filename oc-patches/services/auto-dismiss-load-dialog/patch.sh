#!/bin/bash
#
# Auto-dismiss the load-filament-complete dialog.
#
# Installs:
#   /opt/sbin/synth-tap                — touchscreen tap synthesiser
#   /opt/sbin/auto-dismiss-daemon      — log-tailing daemon
#   /opt/etc/init.d/S99auto-dismiss    — entware service script
#
# All three live under /opt (the entware bind mount), so this patch
# stages them under ${SQUASHFS_ROOT}/app/auto-dismiss-load-dialog/ and
# extends bootstrap.sh / rc.local at boot to copy them into /opt.
# (We can't write directly under ./opt at firmware-build time because
# /opt is bind-mounted from /user-resource at boot.)

if [ $UID -ne 0 ]; then
  echo "Error: Please run as root."
  exit 1
fi

project_root="$REPOSITORY_ROOT"
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"

check_tools "cat install"

set -x
set -e

cd "$SQUASHFS_ROOT"

STAGE_DIR=./app/auto-dismiss-load-dialog
mkdir -p "$STAGE_DIR"

cat "$CURRENT_PATCH_PATH/synth-tap"           > "$STAGE_DIR/synth-tap"
cat "$CURRENT_PATCH_PATH/auto-dismiss-daemon" > "$STAGE_DIR/auto-dismiss-daemon"
cat "$CURRENT_PATCH_PATH/S99auto-dismiss"     > "$STAGE_DIR/S99auto-dismiss"
chmod 755 "$STAGE_DIR/synth-tap" "$STAGE_DIR/auto-dismiss-daemon" "$STAGE_DIR/S99auto-dismiss"

# Hook into rc.local: after the bootstrap_oc block, copy our files into
# /opt and start the service. Idempotent — only adds the hook once.
RC_LOCAL=./etc/rc.local
HOOK_BEGIN='# BEGIN: auto-dismiss-load-dialog'
HOOK_END='# END: auto-dismiss-load-dialog'

if ! grep -q "$HOOK_BEGIN" "$RC_LOCAL"; then
  # Insert before the final 'exit 0', if present; otherwise append.
  TMP=$(mktemp)
  awk -v begin="$HOOK_BEGIN" -v end="$HOOK_END" '
    /^exit 0/ && !inserted {
      print begin
      print "if [ -d /opt/sbin ] && [ -d /opt/etc/init.d ] && [ -f /app/auto-dismiss-load-dialog/auto-dismiss-daemon ]; then"
      print "  cp -f /app/auto-dismiss-load-dialog/synth-tap            /opt/sbin/synth-tap"
      print "  cp -f /app/auto-dismiss-load-dialog/auto-dismiss-daemon  /opt/sbin/auto-dismiss-daemon"
      print "  cp -f /app/auto-dismiss-load-dialog/S99auto-dismiss      /opt/etc/init.d/S99auto-dismiss"
      print "  chmod 755 /opt/sbin/synth-tap /opt/sbin/auto-dismiss-daemon /opt/etc/init.d/S99auto-dismiss"
      print "  /opt/etc/init.d/S99auto-dismiss start &"
      print "fi"
      print end
      print ""
      inserted = 1
    }
    { print }
    END {
      if (!inserted) {
        print begin
        print "[ -f /app/auto-dismiss-load-dialog/auto-dismiss-daemon ] && /opt/etc/init.d/S99auto-dismiss start &"
        print end
      }
    }
  ' "$RC_LOCAL" > "$TMP"
  cat "$TMP" > "$RC_LOCAL"
  rm -f "$TMP"
fi

echo "Installed auto-dismiss-load-dialog patch."
