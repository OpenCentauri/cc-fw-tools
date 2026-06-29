#!/usr/bin/env python3
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
