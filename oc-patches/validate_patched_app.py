#!/usr/bin/env python3
import sys, mmap
from pathlib import Path

# -------------------------------------------------------------------
# Post-patch sanity check for app binary
#   - Verifies total size
#   - Verifies 5 fixed offsets (hard-coded from 1.1.40 app, may (will?) break later or on OC compiled versions
#   - Fail if anything is not as expected (binary is not valid)
#
# Offsets and expected byte values (from unpatched 1.1.40 app):
#   0x00010400 : 0x3E  (early)
#   0x00180000 : 0x08  (random mid)
#   0x002B8218 : 0x81  (after bowden patch area)
#   0x00300000 : 0x04  (random late)
#   0x0035D7DC : 0x54  (after bed mesh temp patch area)
# -------------------------------------------------------------------

# Expected file size in bytes (from unpatched 1.1.40 app)
EXPECTED_SIZE = 3953044

EXPECTED = {
    0x00010400: 0x3E,
    0x00180000: 0x08,
    0x002B8218: 0x81,
    0x00300000: 0x04,
    0x0035D7DC: 0x54,
}

def fail(msg: str, code: int = 1):
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(code)

def main():
    if len(sys.argv) != 2:
        print("usage: verify_binary_spotcheck_fixed.py <binary>", file=sys.stderr)
        sys.exit(2)

    app_path = Path(sys.argv[1])
    if not app_path.is_file():
        fail(f"file not found: {app_path}")

    size = app_path.stat().st_size

    # check size
    if size != EXPECTED_SIZE:
        fail(f"size mismatch: expected {EXPECTED_SIZE} bytes, found {size}")

    # spot-check defined offsets
    oob = [o for o in EXPECTED if o < 0 or o >= size]
    if oob:
        nicetext = ", ".join(f"0x{o:X}" for o in oob)
        fail(f"offset(s) out of range ({size}): {nicetext}")

    mismatches = []
    with app_path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
        for off, expected_val in EXPECTED.items():
            actual_val = m[off]
            if actual_val != expected_val:
                mismatches.append((off, expected_val, actual_val))

    # inform
    if mismatches:
        print(f"[FAIL] {len(mismatches)} / {len(EXPECTED)} mismatches:", file=sys.stderr)
        for (off, exp, got) in mismatches:
            print(f"       off=0x{off:X}  expected=0x{exp:02X}  found=0x{got:02X}", file=sys.stderr)
        sys.exit(1)

    nicetext = ", ".join(f"0x{o:X}" for o in EXPECTED)
    print(f"[OK] binary verified — size {size} bytes, "
          f"{len(EXPECTED)} offsets match ({nicetext})")
    sys.exit(0)

if __name__ == "__main__":
    main()
