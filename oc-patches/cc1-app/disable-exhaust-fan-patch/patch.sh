#!/bin/bash

if [ $UID -ne 0 ]; then
  echo "Error: Please run as root."
  exit 1
fi

set -e

project_root="$REPOSITORY_ROOT"
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"
check_tools "bspatch python3"

verify_1_4_46_bytes() {
  local app_path="$1"
  local state="$2"

  python3 - "$app_path" "$state" <<'PY'
import sys
from pathlib import Path

app_path = Path(sys.argv[1])
state = sys.argv[2]

# app is an ELF loaded at 0x10000; these are virtual addresses in .text.
text_vma = 0x10000
expected = {
    "before": {
        0x0035D508: bytes.fromhex("32 00 00 1a"),  # bne 0x0035d5d8
        0x0035D5D4: bytes.fromhex("cc ff ff 0a"),  # beq 0x0035d50c
    },
    "after": {
        0x0035D508: bytes.fromhex("00 00 a0 e1"),  # nop; fall through to 0x0035d50c
        0x0035D5D4: bytes.fromhex("cc ff ff ea"),  # b 0x0035d50c
    },
}

if state not in expected:
    raise SystemExit(f"unknown verification state: {state}")

data = app_path.read_bytes()
for va, want in expected[state].items():
    offset = va - text_vma
    got = data[offset:offset + len(want)]
    if got != want:
        raise SystemExit(
            f"unexpected {state} bytes at VA 0x{va:08x} "
            f"(file offset 0x{offset:08x}): got {got.hex(' ')}, want {want.hex(' ')}"
        )

print(f"Verified 1.4.46 disable-exhaust-fan {state} bytes")
PY
}

cd "$SQUASHFS_ROOT/app"
if [ "$FW_VER" = "1.1.40" ]; then
  bsdiff_file="exhaust-fan-patch-1.1.40.bsdiff"
elif [ "$FW_VER" = "1.4.46" ]; then
  bsdiff_file="exhaust-fan-patch-1.4.46.bsdiff"
else
  echo "Unsupported firmware version for disable exhaust fan patch: $FW_VER"
  exit 1
fi
cd "$SQUASHFS_ROOT/app"
if [ "$FW_VER" = "1.4.46" ]; then
  verify_1_4_46_bytes ./app before
fi

bspatch ./app ./app-patch "$CURRENT_PATCH_PATH/$bsdiff_file"

if [ "$FW_VER" = "1.4.46" ]; then
  verify_1_4_46_bytes ./app-patch after
fi

rm ./app
mv ./app-patch ./app
