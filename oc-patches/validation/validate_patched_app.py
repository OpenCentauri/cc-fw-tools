#!/usr/bin/env python3
import sys, mmap, hashlib, os, re
from pathlib import Path

# -------------------------------------------------------------------
# Post-patch sanity check for app binary
#   - Verifies total size
#   - Verifies 5 fixed positions (hard-coded from 1.1.40 app, may (will?) break later or on OC compiled versions
#   - Optionally verifies non-excluded regions (whitelist required) via SHA-256 checksum
#   - Fail if anything is not as expected (binary is not valid)
#
# Offsets and expected byte values (from unpatched 1.1.40 app):
#   0x00010400 : 0x3E  
#   0x00180000 : 0x08  
#   0x002B8218 : 0x81  
#   0x00300000 : 0x04  
#   0x0035D7DC : 0x54  
# -------------------------------------------------------------------

# Expected file size in bytes (from unpatched 1.1.40 app)
EXPECTED_SIZE = 3953044

# Expected masked SHA-256 of patched app (patched regions are excluded)
EMBEDDED_MASKED_SHA = "e98d41e382d7dab8c1ccd740b695480435a8883ce538e19218d86a4717e4b12c"

EXPECTED = {
    0x00010400: 0x3E,
    0x00180000: 0x08,
    0x002B8218: 0x81,
    0x00300000: 0x04,
    0x0035D7DC: 0x54,
}

def fail(msg: str, code: int = 1):
    #print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(code)

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def masked_sha256_file(p: Path, ranges: list[tuple[int,int]]) -> str:
    with p.open("rb") as f:
        data = bytearray(f.read())
    for off, ln in ranges:
        if ln <= 0 or off >= len(data):
            continue
        end = min(off + ln, len(data))
        data[off:end] = b"\x00" * (end - off)
    return hashlib.sha256(data).hexdigest()

def _addresses_path() -> Path:
    return Path(__file__).resolve().parent / "patched_addresses"

def _parse_addresses_file(p: Path):
    """Yield (offset,len) pairs from 'patched_addresses' (format: 0xOFFSET 0xLENGTH ... #comment)."""
    if not p.is_file():
        return []
    ranges: list[tuple[int,int]] = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = re.split(r"\s+", line)
        if len(parts) < 2:
            continue
        try:
            off = int(parts[0], 0)
            ln  = int(parts[1], 0)
        except ValueError:
            continue
        if ln > 0:
            ranges.append((off, ln))
    return ranges

def _merge_ranges(ranges):
    if not ranges:
        return []
    ranges = sorted((int(o), int(l)) for o, l in ranges if l > 0)
    out = []
    for o, l in ranges:
        if not out:
            out.append([o, l]); continue
        po, pl = out[-1]
        pe = po + pl
        e  = o + l
        if o <= pe:
            out[-1][1] = max(pe, e) - po
        else:
            out.append([o, l])
    return [(o, l) for o, l in out]

def main():
    if len(sys.argv) != 2:
        print("usage: validate_patched_app.py <binary>", file=sys.stderr)
        sys.exit(2)

    app_path = Path(sys.argv[1])
    if not app_path.is_file():
        fail(f"file not found: {app_path}")

    size = app_path.stat().st_size
    errors = []

    # check size
    if size != EXPECTED_SIZE:
        errors.append(f"size mismatch: expected {EXPECTED_SIZE} bytes, found {size}")

    # spot-check defined offsets (always run; don't exit early on fail)
    oob = [o for o in EXPECTED if o < 0 or o >= size]
    if oob:
        nicetext = ", ".join(f"0x{o:X}" for o in oob)
        errors.append(f"offset(s) out of range ({size}): {nicetext}")

    mismatches = []
    with app_path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
        for off, expected_val in EXPECTED.items():
            actual_val = m[off] if 0 <= off < size else None
            if actual_val != expected_val:
                mismatches.append((off, expected_val, actual_val))

    if mismatches:
        msg_lines = [f"{len(mismatches)} / {len(EXPECTED)} mismatches:"]
        for (off, exp, got) in mismatches:
            got_txt = "N/A" if got is None else f"0x{got:02X}"
            msg_lines.append(f"  off=0x{off:X}  expected=0x{exp:02X}  found={got_txt}")
        errors.append("fixed-byte check failed\n" + "\n".join(msg_lines))
    else:
        nicetext = ", ".join(f"0x{o:X}" for o in EXPECTED)
        #print(f"[VALID] fixed bytes OK — {len(EXPECTED)} offsets match ({nicetext})")

    # full-file SHA
    # print(f"[INFO] sha256={sha256_file(app_path)}")

    # masked SHA
    ranges_file = _addresses_path()
    ranges = _merge_ranges(_parse_addresses_file(ranges_file))
    if not ranges:
        errors.append(f"patched_addresses not found or empty at {ranges_file}")
        masked = None
    else:
        masked = masked_sha256_file(app_path, ranges)
        #print(f"[INFO] masked_sha256={masked}")
        if EMBEDDED_MASKED_SHA:
            if masked != EMBEDDED_MASKED_SHA:
                errors.append(
                    "masked SHA mismatch\n"
                    f"  expected={EMBEDDED_MASKED_SHA}\n"
                    f"  found   ={masked}"
                )
            #else:
                #print("[VALID] masked SHA matches embedded reference")

    # final decision
    if errors:
        print("[FAIL] validation failed:", file=sys.stderr)
        for e in errors:
            print(" - " + e, file=sys.stderr)
        sys.exit(1)

    print("[SUCCESS] all validations passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
