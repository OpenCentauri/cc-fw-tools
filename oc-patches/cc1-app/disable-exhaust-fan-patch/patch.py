#!/usr/bin/env python3
"""Disable automatic exhaust fan during printing (CC1 1.4.49).

Stock 1.4.49 periodic app-top handler (VA 0x35e388) drives the chamber exhaust
fan from chamber temp via helper 0x342784 ("real_fan_speed = %d"). The fan
block (VA 0x35e9e8-0x35ea17) is entered through two print-active paths:
- VA 0x35e920: bne 0x35e9e8  (first path enters fan block)
- VA 0x35e938: bne 0x35ea08  (second entry)

Both branches are NOPed, matching the 1.1.40/1.4.46 intent of skipping the
whole block (not just the final call).
"""

import os

SQUASHFS_ROOT = os.getenv("SQUASHFS_ROOT")
FW_VER = os.getenv("FW_VER", "1.4.49")

if not SQUASHFS_ROOT:
    raise RuntimeError("SQUASHFS_ROOT environment variable is required")
if FW_VER != "1.4.49":
    raise RuntimeError(f"Unsupported firmware version for disable-exhaust-fan patch.py: {FW_VER}")

APP = os.path.join(SQUASHFS_ROOT, "app", "app")
NOP = "0000a0e1"

EDITS = [
    ("exhaust_fan_path1_guard", 0x0034e920, "3000001a", NOP),  # VA 0x35e920 bne -> nop
    ("exhaust_fan_path2_guard", 0x0034e938, "3200001a", NOP),  # VA 0x35e938 bne -> nop
]


def main() -> None:
    with open(APP, "r+b") as fp:
        for label, off, old_hex, _ in EDITS:
            fp.seek(off)
            found = fp.read(len(old_hex) // 2).hex()
            if found != old_hex:
                raise RuntimeError(
                    f"{label}: expected {old_hex} at offset 0x{off:08x}, found {found}; refusing to patch"
                )
        for label, off, _, new_hex in EDITS:
            fp.seek(off)
            fp.write(bytes.fromhex(new_hex))
            print(f"{label}: patched 0x{off:08x} (VA 0x{off + 0x10000:08x})")


if __name__ == "__main__":
    main()
