#!/usr/bin/env bash
set -euo pipefail

if [[ ${UID} -ne 0 ]]; then
  echo "Error: Please run as root." >&2
  exit 1
fi

project_root="${REPOSITORY_ROOT:?REPOSITORY_ROOT is required}"
# shellcheck source=/dev/null
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"
check_tools "bspatch python3"

case "${FW_VER:?FW_VER is required}" in
  1.4.46)
    bsdiff_file="fix-end-print-hang-1.4.46.bsdiff"
    ;;
  *)
    echo "Unsupported firmware version for FIX_END_PRINT_HANG patch: $FW_VER" >&2
    exit 1
    ;;
esac

cd "${SQUASHFS_ROOT:?SQUASHFS_ROOT is required}/app"

python3 "${CURRENT_PATCH_PATH:?CURRENT_PATCH_PATH is required}/verify-${FW_VER}.py" ./app before
bspatch ./app ./app-patch "${CURRENT_PATCH_PATH}/$bsdiff_file"
python3 "$CURRENT_PATCH_PATH/verify-${FW_VER}.py" ./app-patch after

rm ./app
mv ./app-patch ./app
