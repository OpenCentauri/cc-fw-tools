#!/usr/bin/env python3
"""Allow API/status control during printing (CC1 1.4.49).

Stock 1.4.49 set-status API (fcn.00371b10, VA 0x371b10-0x371f7b; srv_control /
sdcp_v3 set-status keys: TempTargetHotbed/Nozzle/Box, ModelFan, ZOffset,
LightStatus, PrintSpeedPct...) rejects changes while printing via a single
guard branch into the "device is busy,can't set status" error flow:
- VA 0x371bcc: subs r2, r0, #0   (r0 = sub_13d53c busy-flag read)
- VA 0x371bd0: bne 0x371e3c      -> error flow

The bne is NOPed, matching the 1.1.40/1.4.46 patch intent (never branch).
"""

import os

SQUASHFS_ROOT = os.getenv("SQUASHFS_ROOT")
FW_VER = os.getenv("FW_VER", "1.4.49")

if not SQUASHFS_ROOT:
    raise RuntimeError("SQUASHFS_ROOT environment variable is required")
if FW_VER != "1.4.49":
    raise RuntimeError(f"Unsupported firmware version for allow-api-during-printing patch.py: {FW_VER}")

APP = os.path.join(SQUASHFS_ROOT, "app", "app")
NOP = "0000a0e1"

EDITS = [
    ("set_status_busy_guard", 0x00361bd0, "9900001a", NOP),  # VA 0x371bd0 bne -> nop
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
