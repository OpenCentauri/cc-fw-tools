#!/usr/bin/env python3
# - this is likely to break other firmware apps completely
# -- TODO:  Write this in a way that is actually safe at some point

#### VERY EXPERIMENTAL - HAVE NOT TRIED PATCH ON CC YET ####
#### IF YOU ARE READING THIS, DO NOT RUN THIS PATCH YET ####

import os
import re
import sys
import struct
import shutil
from pathlib import Path

# -------------------------------------------------------------------
# Bed-mesh temp patch:
#   Replace ASCII "M109 S60" -> "M109 SXX"  (XX comes from BED_MESH_TEMP)
#   Only allow 35–99 inclusive to prevent low temps and byte shift.
#
EXPECTED_BEFORE_HEX = "4D31303920533630"   # hex bytes for ASCII "M109 S60"
# -------------------------------------------------------------------

# rootcheck
if hasattr(os, "geteuid"):
    if os.geteuid() != 0:
        print("[INFO] Skipping: requires root.", file=sys.stderr)
        sys.exit(0)
else:
    print("[INFO] Skipping this patch: root check unavailable on this platform.", file=sys.stderr)
    sys.exit(0)

# env/path
project_root = os.environ.get("REPOSITORY_ROOT")
squashfs_root = os.environ.get("SQUASHFS_ROOT")

if not project_root or not squashfs_root:
    print("Error: REPOSITORY_ROOT and SQUASHFS_ROOT must be set in the environment.", file=sys.stderr)
    sys.exit(1)

project_root = Path(project_root)
squashfs_root = Path(squashfs_root)

# --- read BED_MESH_TEMP from patch_config ---
cfg_file = project_root / "oc-patches" / "patch_config"

# bail for bad data
try:
    cfg_text = cfg_file.read_text(encoding="utf-8", errors="replace")
except FileNotFoundError:
    print("[INFO] BED_MESH_TEMP not found; skipping patch.")
    sys.exit(0)

if "BED_MESH_TEMP=" not in cfg_text:
    print("[INFO] BED_MESH_TEMP not found; skipping patch.")
    sys.exit(0)

# sanitize
m = re.search(r'^BED_MESH_TEMP\s*=\s*([^\r\n#]+)', cfg_text, flags=re.MULTILINE)
if not m:
    print("[INFO] BED_MESH_TEMP not found; skipping patch.")
    sys.exit(0)

temp_raw = m.group(1).strip()
if not re.fullmatch(r'\d+', temp_raw):
    print("[INFO] BED_MESH_TEMP invalid (non-integer); skipping patch.")
    sys.exit(0)

bed_mesh_temp = int(temp_raw, 10)
if not (35 <= bed_mesh_temp <= 99):
    print("[INFO] BED_MESH_TEMP invalid (needs integer 35–99); skipping patch.")
    sys.exit(0)

print(f"[INFO] Applying patch 'Change M109 S60 to S{bed_mesh_temp:02d}'...")

# get app
app_dir = squashfs_root / "app"
orig = app_dir / "app"
work = app_dir / "app-patch"

if not orig.is_file():
    print(f"[INFO] ERROR: target file not found: {orig}", file=sys.stderr)
    sys.exit(1)

shutil.copyfile(orig, work)

try:
    data = bytearray(work.read_bytes())
except Exception as e:
    print(f"[INFO] ERROR: failed to read working file: {e}", file=sys.stderr)
    sys.exit(1)

needle = b"M109 S60"
expected = bytes.fromhex(EXPECTED_BEFORE_HEX)

# This may prevent the entire app from being killed by this change going wrong?  TODO - something better than this
hits = []
start = 0
while True:
    i = data.find(needle, start)
    if i == -1:
        break
    hits.append(i)
    start = i + 1

if len(hits) == 0:
    print(
        f"[INFO] ERROR: pattern 'M109 S60' not found; expected bytes {expected.hex().upper()}\n"
        f"         → skipping patch (bytes don't match, unsafe)",
        file=sys.stderr
    )
    try:
        work.unlink(missing_ok=True)
    except Exception:
        pass
    sys.exit(0)

if len(hits) > 1:
    print(
        f"[INFO] ERROR: pattern 'M109 S60' found {len(hits)} times; "
        f"         → skipping patch (ambiguous, unsafe)",
        file=sys.stderr
    )
    try:
        work.unlink(missing_ok=True)
    except Exception:
        pass
    sys.exit(0)

# write change
hit = hits[0]
before_slice = bytes(data[hit:hit+len(needle)])
if before_slice != expected:
    print(
        f"[INFO] ERROR: pre-patch bytes mismatch at 0x{hit:X}\n"
        f"         found    {before_slice.hex().upper()}\n"
        f"         expected {expected.hex().upper()}\n"
        f"         → skipping patch (unsafe)",
        file=sys.stderr
    )
    try:
        work.unlink(missing_ok=True)
    except Exception:
        pass
    sys.exit(0)

digits_off = hit + len(needle) - 2
data[digits_off:digits_off+2] = f"{bed_mesh_temp:02d}".encode("ascii")

try:
    work.write_bytes(data)
except Exception as e:
    print(f"[INFO] ERROR: failed to write working file: {e}", file=sys.stderr)
    sys.exit(1)

bak = orig.with_suffix(".bak")
try:
    shutil.copyfile(orig, bak)
    shutil.move(str(work), str(orig))
except Exception as e:
    print(f"[INFO] ERROR: failed to replace original app: {e}", file=sys.stderr)
    sys.exit(1)

# Debug only text included, remove later
after_slice = bytes(data[hit:hit+len(needle)])
def _hex(b: bytes) -> str:
    return b.hex().upper()

print(
    f"[INFO] Patch successful — bed-mesh temp set: 'M109 S60' -> 'M109 S{bed_mesh_temp:02d}'  "
    f"-  (DEBUG - at 0x{hit:X}: { _hex(before_slice) } → { _hex(after_slice) })"
)
