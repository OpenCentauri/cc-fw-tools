#!/usr/bin/env bash
set -euo pipefail

if [[ ${UID} -ne 0 ]]; then
  echo "Error: Please run as root." >&2
  exit 1
fi

project_root="${REPOSITORY_ROOT:?REPOSITORY_ROOT is required}"
# shellcheck source=/dev/null
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"
check_tools "bspatch sha256sum python3"

verify_1_4_46_bytes() {
  local app_path="$1"
  local state="$2"

  python3 - "$app_path" "$state" <<'PY'
import sys
from pathlib import Path

BASE_VADDR = 0x10000
app_path = Path(sys.argv[1])
state = sys.argv[2]

expected = {
    "before": {
        0x001B84C4: bytes.fromhex("0f 3d 00 eb"),  # bl sub_1c7908
        0x00450C40: b"\0" * 0x40,
        0x00450D00: b"\0" * 0x80,
    },
    "after": {
        0x001B84C4: bytes.fromhex("0d 62 0a ea"),  # b 0x00450d00
    },
}

if state not in expected:
    raise SystemExit(f"unknown state: {state}")

data = app_path.read_bytes()
for va, want in expected[state].items():
    off = va - BASE_VADDR
    got = data[off:off + len(want)]
    if got != want:
        raise SystemExit(
            f"unexpected {state} bytes at VA 0x{va:08x}: "
            f"got {got.hex(' ')}, want {want.hex(' ')}"
        )

print(f"Verified 1.4.46 FIX_M600_PAUSE {state} bytes")
PY
}

sha256_file() {
  local result
  result=$(sha256sum "$1")
  result=${result%% *}
  printf '%s' "$result"
}

case "${FW_VER:?FW_VER is required}" in
  1.4.46)
    bsdiff_file="fix-m600-pause-1.4.46.bsdiff"
    expected_input_sha256="6d24924bff23083836678a4cda6446c7e6859ec9b9a61fccdc332f611b013b05"
    expected_output_sha256="3bde8bc2255e0d9c2b9878730f2ea4e64ed07047d16df4ae57b2476143cb76fa"
    ;;
  *)
    echo "Unsupported firmware version for FIX_M600_PAUSE patch: $FW_VER" >&2
    exit 1
    ;;
esac

cd "${SQUASHFS_ROOT:?SQUASHFS_ROOT is required}/app"

actual_input_sha256=$(sha256_file ./app)
if [[ "$actual_input_sha256" != "$expected_input_sha256" ]]; then
  echo "Unexpected input app SHA256 for FIX_M600_PAUSE" >&2
  echo "expected: $expected_input_sha256" >&2
  echo "actual:   $actual_input_sha256" >&2
  exit 1
fi

verify_1_4_46_bytes ./app before
bspatch ./app ./app-patch "${CURRENT_PATCH_PATH:?CURRENT_PATCH_PATH is required}/$bsdiff_file"
verify_1_4_46_bytes ./app-patch after

actual_output_sha256=$(sha256_file ./app-patch)
if [[ "$actual_output_sha256" != "$expected_output_sha256" ]]; then
  echo "Unexpected output app SHA256 for FIX_M600_PAUSE" >&2
  echo "expected: $expected_output_sha256" >&2
  echo "actual:   $actual_output_sha256" >&2
  exit 1
fi

rm ./app
mv ./app-patch ./app
