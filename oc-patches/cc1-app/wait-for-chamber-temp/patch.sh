#!/usr/bin/env bash
set -euo pipefail

if [[ ${UID} -ne 0 ]]; then
  echo "Error: Please run as root." >&2
  exit 1
fi

project_root="${REPOSITORY_ROOT:?REPOSITORY_ROOT is required}"
# shellcheck source=/dev/null
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"
check_tools "bspatch"

case "${FW_VER:?FW_VER is required}" in
  1.1.40)
    bsdiff_file="temp_wait_patch-1.1.40.bsdiff"
    ;;
  1.4.46)
    bsdiff_file="temp_wait_patch-1.4.46.bsdiff"
    ;;
  *)
    echo "Unsupported firmware version for wait for chamber temp patch: $FW_VER" >&2
    exit 1
    ;;
esac

cd "${SQUASHFS_ROOT:?SQUASHFS_ROOT is required}/app"
bspatch ./app ./app-patch "${CURRENT_PATCH_PATH:?CURRENT_PATCH_PATH is required}/$bsdiff_file"
rm ./app
mv ./app-patch ./app
