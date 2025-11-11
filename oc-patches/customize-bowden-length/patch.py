#!/usr/bin/env python3
# - Only tested on 1.1.40 app binary

import os
import re
import sys
import struct
import shutil
from pathlib import Path

# -------------------------------------------------------------------
BASE_VA = 0x00010000
TARGET_VA = 0x02C81F8
EXPECTED_BEFORE = bytes.fromhex("0000000000E08540")   # original val for 700mm
DEFAULT_MM = 700                                      # may need to be changed in future hardware/firmware iterations
# -------------------------------------------------------------------

# rootcheck
if hasattr(os, "geteuid") and os.geteuid() != 0:
    print("Error: please run as root.", file=sys.stderr)
    sys.exit(1)

# env/path
project_root = os.environ.get("REPOSITORY_ROOT")
squashfs_root = os.environ.get("SQUASHFS_ROOT")

if not project_root or not squashfs_root:
    print("Error: REPOSITORY_ROOT and SQUASHFS_ROOT must be set in the environment.", file=sys.stderr)
    sys.exit(1)

project_root = Path(project_root)
squashfs_root = Path(squashfs_root)

# --- read BOWDEN_LENGTH_MM from patch_config and validate ---
cfg_file = project_root / "oc-patches" / "patch_config"

try:
    text = cfg_file.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^BOWDEN_LENGTH_MM\s*=\s*([^\r\n#]+)', text, flags=re.MULTILINE)
except FileNotFoundError:
    print("[INFO] Config not found; skipping patch.")
    sys.exit(0)

if not m:
    print("[INFO] BOWDEN_LENGTH_MM not found; skipping patch.")
    sys.exit(0)

# sanitize
bowden_raw = m.group(1).strip()
if not re.fullmatch(r'\d+', bowden_raw):
    print("[INFO] BOWDEN_LENGTH_MM invalid (non-integer); skipping patch.")
    sys.exit(0)

bowden_mm = int(bowden_raw, 10)
if not (10 <= bowden_mm <= 999):
    print("[INFO] BOWDEN_LENGTH_MM invalid (needs integer 10–999); skipping patch.")
    sys.exit(0)

# get app
app_dir = squashfs_root / "app"
orig = app_dir / "app"
work = app_dir / "app-patch"

if not orig.is_file():
    print(f"ERROR: target file not found: {orig}", file=sys.stderr)
    sys.exit(1)

shutil.copyfile(orig, work)

# Hex setup
try:
    data = bytearray(work.read_bytes())
except Exception as e:
    print(f"ERROR: failed to read working file: {e}", file=sys.stderr)
    sys.exit(1)

file_off = TARGET_VA - BASE_VA
if file_off < 0 or file_off + 8 > len(data):
    print(f"ERROR: invalid offset 0x{file_off:X}", file=sys.stderr)
    sys.exit(1)

before = bytes(data[file_off:file_off+8])

# Confirm location
if before != EXPECTED_BEFORE:
    print(
        f"ERROR: pre-patch bytes mismatch at 0x{file_off:X}\n"
        f"       found    {before.hex().upper()}\n"
        f"       expected {EXPECTED_BEFORE.hex().upper()}\n"
        f"       → skipping Bowden patch (bytes don't match, unsafe)",
        file=sys.stderr
    )
    work.unlink(missing_ok=True)
    sys.exit(0)

# write new double bytes
data[file_off:file_off+8] = struct.pack('<d', float(bowden_mm))

# write back to work file
try:
    work.write_bytes(data)
except Exception as e:
    print(f"ERROR: failed to write working file: {e}", file=sys.stderr)
    sys.exit(1)

# Replace
bak = orig.with_suffix(".bak")
try:
    shutil.copyfile(orig, bak)
    shutil.move(str(work), str(orig))
except Exception as e:
    print(f"ERROR: failed to replace original app: {e}", file=sys.stderr)
    sys.exit(1)

old_mm = struct.unpack('<d', before)[0]
new_hex = data[file_off:file_off+8].hex().upper()
print(f"[INFO] Patch successful — Bowden length set to {bowden_mm} mm  "
      f"-  (DEBUG - 0x{TARGET_VA:X} updated from {before.hex().upper()} ({old_mm:.3f} mm) "
      f"to {new_hex} ({float(bowden_mm):.3f} mm))")