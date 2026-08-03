#!/usr/bin/env python3
"""TEMPERATURE_WAIT SENSOR=box support (CC1 1.4.49).

Hooks the stock TEMPERATURE_WAIT handler: the `bl 0xed8d8` (clock) at VA
0x177d88 becomes `b 0x4517f0`, jumping to the trampoline in the rodata zero-run
cave. The trampoline diverts only for SENSOR=box: it waits (usleep 10ms, UI
stays responsive) until chamber temp (srv_state double at state+0x48) is within
MINIMUM/MAXIMUM (d11/d12), then exits to the stock epilogue 0x177f98.

1.4.49 fix vs 1.4.46: non-box sensors re-execute the displaced clock call and
resume the stock handler (0x177d8c) instead of jumping to the epilogue —
stock heater TEMPERATURE_WAIT keeps working.

Trampoline blob: built from trampoline-1.4.49.S (see README-1.4.49.md for the
exact as/ld/objcopy commands). 216 bytes at cave VA 0x4517f0.
"""

import os

SQUASHFS_ROOT = os.getenv("SQUASHFS_ROOT")
FW_VER = os.getenv("FW_VER", "1.4.49")

if not SQUASHFS_ROOT:
    raise RuntimeError("SQUASHFS_ROOT environment variable is required")
if FW_VER != "1.4.49":
    raise RuntimeError(f"Unsupported firmware version for wait-for-chamber-temp patch.py: {FW_VER}")

APP = os.path.join(SQUASHFS_ROOT, "app", "app")

HOOK_OFF = 0x00167d88           # VA 0x177d88
HOOK_OLD = "d2d6fdeb"           # bl 0xed8d8
HOOK_NEW = "98660bea"           # b 0x4517f0

CAVE_OFF = 0x004417f0           # VA 0x4517f0
TRAMPOLINE = "e0d04de234bb8ded36cb8dedf0009de50010d0e5620051e32a00001a0110d0e56f0051e32700001a0210d0e5780051e32400001a0310d0e5000051e32100001afc0004e3440040e30010a0e30020a0e30d30a0e174c80be302c040e33cff2fe1000050e31100001a128b9ded34bb9ded36cb9dede0d08de2c8bbb4ee10faf1ee0500008ac8cbb4ee10faf1ee020000ba98cf07e317c040e31cff2fe1100702e344c50ce301c040e33cff2fe1d3ffffeae0d08de2100702e344c50ce301c040e33cff2fe1cdffffeae0d08de20a00a0e10470f2eb3099f4ea"

KEY_SPAN = 0xD8                 # trampoline size; zero-checked before write


def main() -> None:
    blob = bytes.fromhex(TRAMPOLINE)
    assert len(blob) == KEY_SPAN, f"trampoline blob is {len(blob)} bytes, expected {KEY_SPAN}"
    with open(APP, "r+b") as fp:
        fp.seek(HOOK_OFF)
        found = fp.read(4).hex()
        if found != HOOK_OLD:
            raise RuntimeError(
                f"hook: expected {HOOK_OLD} at offset 0x{HOOK_OFF:08x}, found {found}; refusing to patch"
            )
        fp.seek(CAVE_OFF)
        cave = fp.read(KEY_SPAN)
        if any(cave):
            raise RuntimeError(f"cave at 0x{CAVE_OFF:08x} is not zero-filled; refusing to patch")
        fp.seek(HOOK_OFF)
        fp.write(bytes.fromhex(HOOK_NEW))
        print(f"hook: patched 0x{HOOK_OFF:08x} (VA 0x{HOOK_OFF + 0x10000:08x}) -> b 0x4517f0")
        fp.seek(CAVE_OFF)
        fp.write(blob)
        print(f"cave: wrote {KEY_SPAN}-byte trampoline at 0x{CAVE_OFF:08x} (VA 0x{CAVE_OFF + 0x10000:08x})")


if __name__ == "__main__":
    main()
