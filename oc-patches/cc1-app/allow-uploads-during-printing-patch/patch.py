#!/usr/bin/env python3
"""Allow file uploads during printing (CC1 1.4.49).

Stock 1.4.49 SDCP v3 HTTP handler (fcn.0036a5c8, VA 0x36a5c8-0x36b52b) rejects
uploads while printing via two guard branches into the "device is busy,can't
upload" error flow at VA 0x36b24c:
- VA 0x36acb4: beq  (sub_36c8cc(1)==1 -> busy)
- VA 0x36acdc: bne  (sub_13d53c(busy-flag reader) != 0 -> busy)

Both branches are NOPed, matching the 1.1.40 patch intent (NOP'd beq+bne pair).
"""

import os

SQUASHFS_ROOT = os.getenv("SQUASHFS_ROOT")
FW_VER = os.getenv("FW_VER", "1.4.49")

if not SQUASHFS_ROOT:
    raise RuntimeError("SQUASHFS_ROOT environment variable is required")
if FW_VER != "1.4.49":
    raise RuntimeError(f"Unsupported firmware version for allow-uploads-during-printing patch.py: {FW_VER}")

APP = os.path.join(SQUASHFS_ROOT, "app", "app")
NOP = "0000a0e1"

# (label, file offset, expected LE bytes, new LE bytes); file offset = VA - 0x10000
EDITS = [
    ("upload_guard_print_state", 0x0035acb4, "6401000a", NOP),  # VA 0x36acb4 beq -> nop
    ("upload_guard_busy_flag",   0x0035acdc, "5a01001a", NOP),  # VA 0x36acdc bne -> nop
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
