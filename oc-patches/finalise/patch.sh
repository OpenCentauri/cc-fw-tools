#!/bin/bash

set -e

cat ./rc.local >> "$SQUASHFS_ROOT/etc/rc.local"

# Add binary verification due to configurable patches introducing potential instability
# Needs cleanup tasks if pack.sh is not to be run due to failed validation
echo "Running final post-patch validation..."
APP_PATH="$SQUASHFS_ROOT/app/app"
if [ -f "$APP_PATH" ]; then
    python3 "$PATCHES_ROOT/validate_patched_app.py" "$APP_PATH"
    if [ $? -ne 0 ]; then
        echo "[ERROR] Binary validation failed — aborting finalization."
        exit 1
    else
        echo "[VALID] Post-patch validation passed."
    fi
else
    echo "[WARN] app binary not found at $APP_PATH — skipping validation."
fi