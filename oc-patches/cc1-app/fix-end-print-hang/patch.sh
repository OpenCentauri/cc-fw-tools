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
        0x0035DBA4: bytes.fromhex("2c 56 c4 e5"),  # strb r5, [r4, #0x62c]
        0x0035DBA8: bytes.fromhex("96 55 c4 e5"),  # strb r5, [r4, #0x596]
        0x00450B00: b"\0" * 0x80,
        0x00450C00: b"\0" * 0x40,
    },
    "after": {
        0x0035DBA4: bytes.fromhex("d5 cb 03 ea"),  # b 0x00450b00
        0x0035DBA8: bytes.fromhex("96 55 c4 e5"),  # unchanged in file; replayed in trampoline
        0x00450C00: b"M117 OpenCentauri Print Complete\0",
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

print(f"Verified 1.4.46 FIX_END_PRINT_HANG {state} bytes")
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
    bsdiff_file="fix-end-print-hang-1.4.46.bsdiff"
    expected_input_sha256="80e636221be0843793e2283d364b68dea7ced9ae744bf9c09798d0970d5e9cf3"
    expected_output_sha256="6d24924bff23083836678a4cda6446c7e6859ec9b9a61fccdc332f611b013b05"
    ;;
  *)
    echo "Unsupported firmware version for FIX_END_PRINT_HANG patch: $FW_VER" >&2
    exit 1
    ;;
esac

cd "${SQUASHFS_ROOT:?SQUASHFS_ROOT is required}/app"

actual_input_sha256=$(sha256_file ./app)
if [[ "$actual_input_sha256" != "$expected_input_sha256" ]]; then
  echo "Unexpected input app SHA256 for FIX_END_PRINT_HANG" >&2
  echo "expected: $expected_input_sha256" >&2
  echo "actual:   $actual_input_sha256" >&2
  exit 1
fi

verify_1_4_46_bytes ./app before
bspatch ./app ./app-patch "${CURRENT_PATCH_PATH:?CURRENT_PATCH_PATH is required}/$bsdiff_file"
verify_1_4_46_bytes ./app-patch after

actual_output_sha256=$(sha256_file ./app-patch)
if [[ "$actual_output_sha256" != "$expected_output_sha256" ]]; then
  echo "Unexpected output app SHA256 for FIX_END_PRINT_HANG" >&2
  echo "expected: $expected_output_sha256" >&2
  echo "actual:   $actual_output_sha256" >&2
  exit 1
fi

rm ./app
mv ./app-patch ./app
