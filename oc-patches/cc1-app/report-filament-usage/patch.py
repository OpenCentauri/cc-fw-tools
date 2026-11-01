#!/usr/bin/env python3
"""CC1 1.4.49 SDCP filament usage, based on harpua555's PR #40.

Patch the broadcast PrintInfo writer and reserve private zero-initialized BSS.
Validate every region before writing any byte; never reuse stock PRNG storage.
"""
import os
from pathlib import Path
import struct

HOOK_OFF = 0x35d310
HOOK_OLD = "451040e3903a07ee670bb8ee"
HOOK_NEW = "d0c801e345c040e31cff2fe1"
CAVE_OFF = 0x4418d0
FN = "ff002de902cb2ded451040e3903a07ee670bb8ee0800a0e180cb09e32cc040e33cff2fe1bc0702e34b0040e3000090e5f80090e5070d80e2d020c0e1102b43ec085f02e3525040e3d060c5e11c6b47ecf020c5e14c0b30ee106b57ec105f02e3525040e3f060c5e10800a0e1a01901e3451040e3085f02e3525040e3d060c5e1106b47ec80cb09e32cc040e33cff2fe10800a0e1b01901e3451040e3105f02e3525040e3d060c5e1106b47ec80cb09e32cc040e33cff2fe102cbbdecff00bde8626efcea"
FN_SIZE = 196
KEY1_OFF = 0x4419a0
KEY1 = b"TotalExtrusion\0"
KEY2_OFF = 0x4419b0
KEY2 = b"CurrentExtrusion\0"
ELF_EDITS = ((0xc8, 0x741fc, 0x74210),
             (0x492380, 0x710d4, 0x710e8),
             (0x1724, 0x522f04, 0x522f18),
             (0x20a4, 0x522f04, 0x522f18),
             (0x3e34, 0x522f04, 0x522f18),
             (0x4044, 0x522f04, 0x522f18))


def main():
    root = os.environ.get("SQUASHFS_ROOT")
    if not root:
        raise RuntimeError("SQUASHFS_ROOT environment variable is required")
    if os.environ.get("FW_VER", "1.4.49") != "1.4.49":
        raise RuntimeError("report-filament-usage patch.py only supports 1.4.49")
    blob = bytes.fromhex(FN)
    if len(blob) != FN_SIZE:
        raise RuntimeError("injected blob must be 196 bytes")
    writes = [(HOOK_OFF, bytes.fromhex(HOOK_NEW)), (CAVE_OFF, blob),
              (KEY1_OFF, KEY1), (KEY2_OFF, KEY2)]
    guards = [(HOOK_OFF, bytes.fromhex(HOOK_OLD)),
              (0x35d30c, bytes.fromhex("d01609e3")),
              (0x35d31c, bytes.fromhex("1772fdeb")),
              (CAVE_OFF, bytes(FN_SIZE)),
              (KEY1_OFF, bytes(len(KEY1))), (KEY2_OFF, bytes(len(KEY2)))]
    for offset, old, new in ELF_EDITS:
        guards.append((offset, struct.pack("<I", old)))
        writes.append((offset, struct.pack("<I", new)))
    app = Path(root) / "app/app"
    with app.open("r+b") as stream:
        data = stream.read()
        if len(data) != 4793356 or data[:7] != b"\x7fELF\x01\x01\x01":
            raise RuntimeError("unexpected ELF size or identity; refusing to patch")
        for offset, expected in guards:
            found = data[offset:offset + len(expected)]
            if found != expected:
                raise RuntimeError(f"guard mismatch at file 0x{offset:x}; refusing to patch")
        for offset, payload in writes:
            stream.seek(offset)
            stream.write(payload)
    print("report_filament_usage: SDCP hook 0x36d310, scratch 0x522f08/0x522f10 reserved")


if __name__ == "__main__":
    main()
