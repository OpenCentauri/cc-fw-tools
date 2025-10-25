#!/usr/bin/env bash
set -euo pipefail

# - this is likely to break other firmware apps completely
# -- TODO:  Write this in a way that is actually safe at some point
BASE_VA=0x00010000
TARGET_VA=0x02C81F8
EXPECTED_BEFORE_HEX="0000000000E08540"   # original val for 700mm
DEFAULT_MM=700                           # don't waste time if val isn't changed.  TODO - this, but in a better way
# -------------------------------------------------------------------

if [[ $UID -ne 0 ]]; then
  echo "Error: please run as root." >&2
  exit 1
fi

project_root="$REPOSITORY_ROOT"
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"
check_tools "bsdiff bspatch python3"

# --- read BOWDEN_LENGTH_MM from patch_config and validate ---
cfg_file="$project_root/oc-patches/patch_config"

# bail for bad data
if [[ ! -f "$cfg_file" ]] || ! grep -qE '^BOWDEN_LENGTH_MM=' "$cfg_file"; then
  echo "[INFO] BOWDEN_LENGTH_MM not found; skipping patch."
  exit 0
fi

# extract value, strip whitespace
bowden_mm="$(awk -F= '/^BOWDEN_LENGTH_MM=/{gsub(/[ \t\r]/,"",$2); sub(/#.*/,"",$2); print $2}' "$cfg_file")"

# validate BOWDEN_LENGTH_MM (must be 10–999 integer)
if [[ "$bowden_mm" =~ ^[0-9]+$ ]]; then
  val=$((10#$bowden_mm))
  if (( val >= 10 && val <= 999 )); then
    bowden_mm=$val
  else
    echo "[INFO] BOWDEN_LENGTH_MM invalid (needs integer 10–999); skipping patch."
    exit 0
  fi
else
  echo "[INFO] BOWDEN_LENGTH_MM invalid (non-integer); skipping patch."
  exit 0
fi

echo "[INFO] Applying patch 'Custom bowden length'...  (target length: ${bowden_mm} mm)"

# get app
cd "$SQUASHFS_ROOT/app"
orig="./app"
work="./app-patch"
cp -f "$orig" "$work"

# Custom offset hex
python3 - "$work" "$bowden_mm" "$EXPECTED_BEFORE_HEX" "$BASE_VA" "$TARGET_VA" <<'PY'
import sys, struct

app, mm_str, expected_hex, base_va_str, target_va_str = sys.argv[1:6]
mm = int(mm_str)
base_va = int(base_va_str,16)
target_va = int(target_va_str,16)
file_off = target_va - base_va

with open(app,'rb') as f:
    data = bytearray(f.read())
if file_off < 0 or file_off+8 > len(data):
    raise SystemExit(f"[INFO] ERROR: invalid offset 0x{file_off:X}")
before = bytes(data[file_off:file_off+8])
expected = bytes.fromhex(expected_hex)
# This may prevent the entire app from being killed by this change going wrong?  TODO - something better than this
if before != expected:
    print(
        f"[INFO] ERROR: pre-patch bytes mismatch at 0x{file_off:X}\n"
        f"         found    {before.hex().upper()}\n"
        f"         expected {expected.hex().upper()}\n"
        f"         → skipping Bowden patch (bytes don't match, unsafe)",
        file=sys.stderr
    )
    sys.exit(0)

data[file_off:file_off+8] = struct.pack('<d', float(mm))  # little-endian double
with open(app,'wb') as f: f.write(data)

# Debug only, remove later
old_mm = struct.unpack('<d', before)[0]
new_mm = mm
old_hex = before.hex().upper()
new_hex = data[file_off:file_off+8].hex().upper()

print(f"[INFO] Patch successful — Bowden length set to {int(new_mm)} mm  "
      f"-  (DEBUG - 0x{target_va:X} updated from {old_hex} ({old_mm:.3f} mm) "
      f"to {new_hex} ({new_mm:.3f} mm))")
PY

#
# OTF bsdiff create / apply / cleanup
tmp_patch="$(mktemp --suffix=.bsdiff)"
bsdiff "$orig" "$work" "$tmp_patch"
bspatch "$orig" "$work" "$tmp_patch"
mv -f "$work" "$orig"
rm -f "$tmp_patch"