#!/usr/bin/env python3
# - this is likely to break other firmware apps completely
# -- TODO:  Write this in a way that is actually safe at some point

import os
import re
import sys
import struct
import shutil
from pathlib import Path

# -------------------------------------------------------------------
BASE_VA = 0x00010000
TARGET_VA = 0x02C81F8
EXPECTED_BEFORE_HEX = "0000000000E08540"   # original val for 700mm
DEFAULT_MM = 700                           # don't waste time if val isn't changed.  TODO - this, but in a better way
# -------------------------------------------------------------------

# rootcheck
if hasattr(os, "geteuid"):
    if os.geteuid() != 0:
        print("Error: please run as root.", file=sys.stderr)
        sys.exit(1)
else:
    # On platforms without geteuid (rare in your flow), just warn.
    print("[WARN] Root check unavailable on this platform; proceeding.")

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

# bail for bad data
if (not cfg_file.is_file()) or ("BOWDEN_LENGTH_MM=" not in cfg_file.read_text(encoding="utf-8", errors="replace")):
    print("[INFO] BOWDEN_LENGTH_MM not found; skipping patch.")
    sys.exit(0)

# sanitize
text = cfg_file.read_text(encoding="utf-8", errors="replace")
m = re.search(r'^BOWDEN_LENGTH_MM\s*=\s*([^\r\n#]+)', text, flags=re.MULTILINE)
if not m:
    print("[INFO] BOWDEN_LENGTH_MM not found; skipping patch.")
    sys.exit(0)

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
    print(f"[INFO] ERROR: target file not found: {orig}", file=sys.stderr)
    sys.exit(1)

shutil.copyfile(orig, work)

# Hex setup
try:
    data = bytearray(work.read_bytes())
except Exception as e:
    print(f"[INFO] ERROR: failed to read working file: {e}", file=sys.stderr)
    sys.exit(1)

file_off = TARGET_VA - BASE_VA
if file_off < 0 or file_off + 8 > len(data):
    print(f"[INFO] ERROR: invalid offset 0x{file_off:X}", file=sys.stderr)
    sys.exit(1)

before = bytes(data[file_off:file_off+8])
expected = bytes.fromhex(EXPECTED_BEFORE_HEX)

# This may prevent the entire app from being killed by this change going wrong?  TODO - something better than this
if before != expected:
    print(
        f"[INFO] ERROR: pre-patch bytes mismatch at 0x{file_off:X}\n"
        f"         found    {before.hex().upper()}\n"
        f"         expected {expected.hex().upper()}\n"
        f"         → skipping Bowden patch (bytes don't match, unsafe)",
        file=sys.stderr
    )
    try:
        work.unlink(missing_ok=True)
    except Exception:
        pass
    sys.exit(0)

# write new double bytes
data[file_off:file_off+8] = struct.pack('<d', float(bowden_mm))

# write back to work file
try:
    work.write_bytes(data)
except Exception as e:
    print(f"[INFO] ERROR: failed to write working file: {e}", file=sys.stderr)
    sys.exit(1)

# Replace original with patched app
bak = orig.with_suffix(".bak")
try:
    shutil.copyfile(orig, bak)
    shutil.move(str(work), str(orig))
except Exception as e:
    print(f"[INFO] ERROR: failed to replace original app: {e}", file=sys.stderr)
    sys.exit(1)

# Debug only text included, remove later
old_mm = struct.unpack('<d', before)[0]
new_hex = data[file_off:file_off+8].hex().upper()
print(f"[INFO] Patch successful — Bowden length set to {bowden_mm} mm  "
      f"-  (DEBUG - 0x{TARGET_VA:X} updated from {before.hex().upper()} ({old_mm:.3f} mm) "
      f"to {new_hex} ({float(bowden_mm):.3f} mm))")
