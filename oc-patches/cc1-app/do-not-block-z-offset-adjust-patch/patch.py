#!/usr/bin/env python3
"""Always allow z-offset adjustment during printing (CC1 1.4.49).

Stock 1.4.49 app_z_offset_callback (fcn.0034cb60, VA 0x34cb60-0x34d44f) blocks
z-offset buttons while printing via
  if (app_print_get_print_state() && (!app_print_get_print_busy() || !app_top_get_autoleveling_busy()))
(Elegoo source: app_setting.cpp). Both button paths (BTN_DOWN / BTN_UP) start
with `bl 0x342a78` (print_state getter) feeding that condition.

The patch replaces each `bl` with an unconditional branch into the adjust body,
matching the 1.1.40 patch intent (identical relative deltas: ea000004 /
ea000046):
- VA 0x34cc44 (BTN_DOWN): bl 0x342a78 -> b 0x34cc5c
- VA 0x34d20c (BTN_UP):   bl 0x342a78 -> b 0x34d32c
"""

import os

SQUASHFS_ROOT = os.getenv("SQUASHFS_ROOT")
FW_VER = os.getenv("FW_VER", "1.4.49")

if not SQUASHFS_ROOT:
    raise RuntimeError("SQUASHFS_ROOT environment variable is required")
if FW_VER != "1.4.49":
    raise RuntimeError(f"Unsupported firmware version for do-not-block-z-offset-adjust patch.py: {FW_VER}")

APP = os.path.join(SQUASHFS_ROOT, "app", "app")

EDITS = [
    ("z_offset_btn_down", 0x0033cc44, "8bd7ffeb", "040000ea"),  # VA 0x34cc44 bl -> b 0x34cc5c
    ("z_offset_btn_up",   0x0033d20c, "19d6ffeb", "460000ea"),  # VA 0x34d20c bl -> b 0x34d32c
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
