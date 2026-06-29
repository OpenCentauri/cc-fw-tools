#!/bin/bash

if [ $UID -ne 0 ]; then
  echo "Error: Please run as root."
  exit 1
fi

set -e

project_root="$REPOSITORY_ROOT"
# shellcheck source=/dev/null
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"
check_tools "bspatch"

if [ "$FW_VER" = "1.4.46" ]; then
  bsdiff_file="fix-noncanvas-load-1.4.46.bsdiff"
else
  echo "Unsupported firmware version for fix non-Canvas load patch: $FW_VER"
  exit 1
fi

cd "$SQUASHFS_ROOT/app"
bspatch ./app ./app-patch "$CURRENT_PATCH_PATH/$bsdiff_file"
rm ./app
mv ./app-patch ./app
