#!/usr/bin/env python3
"""Report filament usage in PrintStats JSON (CC1 1.4.49).

Hooks the SDCP status JSON writer at VA 0x37f9ec (the "printing"-path
TotalLayer emission): the 12-byte movw/movt/vcvt triplet becomes
`movw ip,#0x18d0; movt ip,#0x45; bx ip` into the cave fn at 0x4518d0, which
replays the triplet, emits TotalLayer (stock helper 0x2c9b80), then emits
TotalExtrusion (cumulative E from [[0x4b27bc]+0xf8]+0x1c0) and CurrentExtrusion
(per-cycle delta, state doubles at 0x4b4788/0x4b4790), then resumes at
0x37f9fc.

Key strings "TotalExtrusion\0" @ 0x4519a0 and "CurrentExtrusion\0" @ 0x4519b0
are written by this script (exact 1.4.46 strings — HA integration contract).

Injected fn blob: built from injected-1.4.49.S (see README-1.4.49.md). 196
bytes at cave VA 0x4518d0. The bss state doubles are runtime-zero (no file
backing) — not byte-guardable, documented in the README.
"""

import os

SQUASHFS_ROOT = os.getenv("SQUASHFS_ROOT")
FW_VER = os.getenv("FW_VER", "1.4.49")

if not SQUASHFS_ROOT:
    raise RuntimeError("SQUASHFS_ROOT environment variable is required")
if FW_VER != "1.4.49":
    raise RuntimeError(f"Unsupported firmware version for report-filament-usage patch.py: {FW_VER}")

APP = os.path.join(SQUASHFS_ROOT, "app", "app")

HOOK_OFF = 0x0036f9ec           # VA 0x37f9ec
HOOK_OLD = "d01609e3451040e3670bb8ee"  # movw r1,#0x96d0; movt r1,#0x45; vcvt.f64.u32 d0,s15
HOOK_NEW = "d0c801e345c040e31cff2fe1"  # movw ip,#0x18d0; movt ip,#0x45; bx ip

CAVE_OFF = 0x004418d0           # VA 0x4518d0
FN = "ff002de902cb2dedd01609e3451040e3670bb8ee0400a0e180cb09e32cc040e33cff2fe1bc0702e34b0040e3000090e5f80090e5070d80e2d020c0e1102b43ec885704e34b5040e3d060c5e11c6b47ecf020c5e14c0b30ee106b57ec905704e34b5040e3f060c5e10400a0e1a01901e3451040e3885704e34b5040e3d060c5e1106b47ec80cb09e32cc040e33cff2fe10400a0e1b01901e3451040e3905704e34b5040e3d060c5e1106b47ec80cb09e32cc040e33cff2fe102cbbdecff00bde819b8fcea"
FN_SIZE = 196

KEY1_OFF = 0x004419a0           # VA 0x4519a0
KEY1 = b"TotalExtrusion\x00"
KEY2_OFF = 0x004419b0           # VA 0x4519b0
KEY2 = b"CurrentExtrusion\x00"


def main() -> None:
    blob = bytes.fromhex(FN)
    assert len(blob) == FN_SIZE, f"injected blob is {len(blob)} bytes, expected {FN_SIZE}"
    with open(APP, "r+b") as fp:
        fp.seek(HOOK_OFF)
        found = fp.read(12).hex()
        if found != HOOK_OLD:
            raise RuntimeError(
                f"hook: expected {HOOK_OLD} at offset 0x{HOOK_OFF:08x}, found {found}; refusing to patch"
            )
        for off, data, label in ((CAVE_OFF, blob, "cave"), (KEY1_OFF, KEY1, "key1"), (KEY2_OFF, KEY2, "key2")):
            fp.seek(off)
            cur = fp.read(len(data))
            if any(cur):
                raise RuntimeError(f"{label} region at 0x{off:08x} is not zero-filled; refusing to patch")
        fp.seek(HOOK_OFF)
        fp.write(bytes.fromhex(HOOK_NEW))
        print(f"hook: patched 0x{HOOK_OFF:08x} (VA 0x{HOOK_OFF + 0x10000:08x}) -> bx 0x4518d0")
        fp.seek(CAVE_OFF)
        fp.write(blob)
        print(f"cave: wrote {FN_SIZE}-byte fn at 0x{CAVE_OFF:08x} (VA 0x{CAVE_OFF + 0x10000:08x})")
        fp.seek(KEY1_OFF)
        fp.write(KEY1)
        fp.seek(KEY2_OFF)
        fp.write(KEY2)
        print(f"keys: wrote TotalExtrusion/CurrentExtrusion at VA 0x4519a0/0x4519b0")


if __name__ == "__main__":
    main()
