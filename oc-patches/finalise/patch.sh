#!/bin/bash

set -e

cat ./rc.local >> "$SQUASHFS_ROOT/etc/rc.local"

# Add binary verification due to configurable patches introducing potential instability
echo "Running final post-patch validation..."
APP_PATH="$SQUASHFS_ROOT/app/app"
if [ -f "$APP_PATH" ]; then
    python3 "$PATCHES_ROOT/validation/validate_patched_app.py" "$APP_PATH"
    echo "[VALID] Post-patch validation passed."
else
    echo "[WARN] app binary not found at $APP_PATH — skipping validation.  CANNOT VERIFY FIRMWARE INTEGRITY!"
fi