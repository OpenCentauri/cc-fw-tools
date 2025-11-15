#!/bin/bash

if [ $UID -ne 0 ]; then
  echo "Error: Please run as root."
  exit 1
fi

set -e

project_root="$REPOSITORY_ROOT"
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"
check_tools "bspatch"

cd "$SQUASHFS_ROOT/app"
bspatch ./app ./app-patch "$CURRENT_PATCH_PATH/report_filament_usage_patch.bsdiff"
rm ./app
mv ./app-patch ./app