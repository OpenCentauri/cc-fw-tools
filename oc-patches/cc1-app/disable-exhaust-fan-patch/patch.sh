#!/bin/bash

if [ $UID -ne 0 ]; then
  echo "Error: Please run as root."
  exit 1
fi

set -e

project_root="$REPOSITORY_ROOT"
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"
check_tools "bspatch python3"

cd "$SQUASHFS_ROOT/app"
if [ "$FW_VER" = "1.1.40" ]; then
  bsdiff_file="exhaust-fan-patch-1.1.40.bsdiff"
elif [ "$FW_VER" = "1.4.46" ]; then
  bsdiff_file="exhaust-fan-patch-1.4.46.bsdiff"
elif [ "$FW_VER" = "1.4.49" ]; then
  python3 "$CURRENT_PATCH_PATH/patch.py"
  exit 0
else
  echo "Unsupported firmware version for disable exhaust fan patch: $FW_VER"
  exit 1
fi
cd "$SQUASHFS_ROOT/app"
if [ "$FW_VER" = "1.4.46" ]; then
  if [ -f "$CURRENT_PATCH_PATH/verify-${FW_VER}.py" ]; then
    python3 "$CURRENT_PATCH_PATH/verify-${FW_VER}.py" ./app before
  fi
fi

bspatch ./app ./app-patch "$CURRENT_PATCH_PATH/$bsdiff_file"

if [ "$FW_VER" = "1.4.46" ]; then
  if [ -f "$CURRENT_PATCH_PATH/verify-${FW_VER}.py" ]; then
    python3 "$CURRENT_PATCH_PATH/verify-${FW_VER}.py" ./app-patch after
  fi
fi

rm ./app
mv ./app-patch ./app
