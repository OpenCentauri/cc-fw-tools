#!/bin/bash

if [ $UID -ne 0 ]; then
  echo "Error: Please run as root."
  exit 1
fi

set -e

project_root="$REPOSITORY_ROOT"
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"
check_tools "bspatch"

if [ "$FW_VER" = "1.1.40" ]; then
  bsdiff_file="add-chamber-light-gcode-1.1.40.bsdiff"
elif [ "$FW_VER" = "1.4.46" ]; then
  bsdiff_file="add-chamber-light-gcode-1.4.46.bsdiff"
elif [ "$FW_VER" = "1.4.49" ]; then
  bsdiff_file="add-chamber-light-gcode-1.4.49.bsdiff"
  verify_file="verify-1.4.49.py"
else
  echo "Unsupported firmware version for add chamber light gcode patch: $FW_VER"
  exit 1
fi

cd "$SQUASHFS_ROOT/app"
if [ -n "$verify_file" ]; then
  python3 "$CURRENT_PATCH_PATH/$verify_file" ./app before
fi
bspatch ./app ./app-patch "$CURRENT_PATCH_PATH/$bsdiff_file"
if [ -n "$verify_file" ]; then
  python3 "$CURRENT_PATCH_PATH/$verify_file" ./app-patch after
fi
rm ./app
mv ./app-patch ./app
