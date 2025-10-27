#!/usr/bin/env python3
# - Only tested on 1.1.40 app binary

import os
import re
import sys
import shutil
from pathlib import Path

# -------------------------------------------------------------------
# Bed-mesh temp patch:
#   Replace "M190 S60" -> "M190 SXX"  (XX comes from BED_MESH_TEMP in patch_config)
#   Only allow 35–99 inclusive to prevent low temps and byte shift.
#
BASE_VA = 0x00010000                       # base address
TARGET_VA = 0x036D7BC                      # address of string "M190 S60" (data_36d7bc)
EXPECTED_BEFORE = bytes.fromhex("4D31393020533630")  # "M190 S60"
# -------------------------------------------------------------------

# rootcheck
if hasattr(os, "geteuid") and os.geteuid() != 0:
    print("[INFO] Skipping: requires root.", file=sys.stderr)
    sys.exit(0)

# env/path
project_root = os.environ.get("REPOSITORY_ROOT")
squashfs_root = os.environ.get("SQUASHFS_ROOT")

if not project_root or not squashfs_root:
    print("Error: REPOSITORY_ROOT and SQUASHFS_ROOT must be set in the environment.", file=sys.stderr)
    sys.exit(1)

project_root = Path(project_root)
squashfs_root = Path(squashfs_root)

# read BED_MESH_TEMP from patch_config
cfg_file = project_root / "oc-patches" / "patch_config"

try:
    cfg_text = cfg_file.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^BED_MESH_TEMP\s*=\s*([^\r\n#]+)', cfg_text, flags=re.MULTILINE)
except FileNotFoundError:
    print("[INFO] Config file not found; skipping patch.")
    sys.exit(0)

if not m:
    print("[INFO] BED_MESH_TEMP not found in config; skipping patch.")
    sys.exit(0)

# sanitize
temp_raw = m.group(1).strip()
if not re.fullmatch(r'\d+', temp_raw):
    print("[INFO] BED_MESH_TEMP invalid (non-integer); skipping patch.")
    sys.exit(0)

bed_mesh_temp = int(temp_raw, 10)
if not (35 <= bed_mesh_temp <= 99):
    print("[INFO] BED_MESH_TEMP invalid (requires integer 35–99); skipping patch.")
    sys.exit(0)

# skip if no change (60 in cfg)
if bed_mesh_temp == 60:
    print("[INFO] BED_MESH_TEMP is set to 60 (stock) - no change; skipping patch.")
    sys.exit(0)

# get app
app_dir = squashfs_root / "app"
orig = app_dir / "app"
work = app_dir / "app-patch"

if not orig.is_file():
    print(f"ERROR: target file not found: {orig}", file=sys.stderr)
    sys.exit(1)

shutil.copyfile(orig, work)

try:
    data = bytearray(work.read_bytes())
except Exception as e:
    print(f"ERROR: failed to read working file: {e}", file=sys.stderr)
    sys.exit(1)

# Check/find
file_off = TARGET_VA - BASE_VA
if file_off < 0 or file_off + 8 > len(data):
    print(f"ERROR: invalid offset 0x{file_off:X}", file=sys.stderr)
    work.unlink(missing_ok=True)
    sys.exit(0)

before_slice = bytes(data[file_off:file_off+8])

# Confirm location
if before_slice != EXPECTED_BEFORE:
    print(
        f"ERROR: pre-patch bytes mismatch at 0x{file_off:X}\n"
        f"       found    {before_slice.hex().upper()}\n"
        f"       expected {EXPECTED_BEFORE.hex().upper()}\n"
        f"       → skipping patch (unsafe)",
        file=sys.stderr
    )
    work.unlink(missing_ok=True)
    sys.exit(0)

# write change: keep "M190 S", change last two digits
digits_off = file_off + 6
data[digits_off:digits_off+2] = f"{bed_mesh_temp:02d}".encode("ascii")

try:
    work.write_bytes(data)
except Exception as e:
    print(f"ERROR: failed to write working file: {e}", file=sys.stderr)
    sys.exit(1)

bak = orig.with_suffix(".bak")
try:
    shutil.copyfile(orig, bak)
    shutil.move(str(work), str(orig))
except Exception as e:
    print(f"ERROR: failed to replace original app: {e}", file=sys.stderr)
    sys.exit(1)

after_slice = bytes(data[file_off:file_off+8])
print(
    f"[INFO] Patch successful — bed-mesh temp set: 'M190 S60' -> 'M190 S{bed_mesh_temp:02d}'  "
    f"-  (DEBUG - at 0x{file_off:X}: {before_slice.hex().upper()} → {after_slice.hex().upper()})"
)