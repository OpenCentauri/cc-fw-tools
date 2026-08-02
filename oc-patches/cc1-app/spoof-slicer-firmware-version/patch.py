#!/usr/bin/env python3
"""Spoof the firmware version reported to ElegooSlicer in SDCP attribute responses.

Stock CC1 1.4.49 reads the version string from VA 0x0040ae10 for:
- UDP discovery responses (VA 0x00369974)
- WebSocket/MQTT attributes topic (VA 0x0036bd64)
- Direct request-attribute responses (VA 0x0037fbe4)

This patch repoints the source pointer in all three functions to a new code cave at
VA 0x004517e0 containing a fixed "1.4.49\\0" string. The original version string at
VA 0x0040ae10 (logs, UI, OTA) is left untouched.
"""

import os
import sys

SQUASHFS_ROOT = os.getenv("SQUASHFS_ROOT")
FW_VER = os.getenv("FW_VER", "1.4.49")

if not SQUASHFS_ROOT:
    raise RuntimeError("SQUASHFS_ROOT environment variable is required")
if FW_VER != "1.4.49":
    raise RuntimeError(f"Unsupported firmware version for spoof-slicer-firmware-version patch: {FW_VER}")

APP = os.path.join(SQUASHFS_ROOT, "app", "app")

# File offsets (VA - 0x00010000, single LOAD segment starts at VA 0x10000/file 0).
UDP_VERSION_PTR = 0x00359974      # VA 0x00369974
WS_VERSION_PTR = 0x0035bd64       # VA 0x0036bd64
REQ_VERSION_PTR = 0x0036fbe4      # VA 0x0037fbe4
CAVE_VA = 0x004517e0              # 2KB zero run in .rodata; see AGENT-1.4.49.md cave table
CAVE_FILE_OFFSET = CAVE_VA - 0x00010000

EXPECTED_OLD = bytes.fromhex("103e0ae3403040e3")  # movw r3,#0xae10; movt r3,#0x40
NEW_BYTES = bytes.fromhex("e03701e3453040e3")     # movw r3,#0x17e0; movt r3,#0x45
CAVE_STRING = b"1.4.49\x00"     # 7 bytes, matching the stock 7-byte version slot


def patch_movw_movt(label: str, offset: int) -> None:
    with open(APP, "r+b") as fp:
        fp.seek(offset)
        old = fp.read(8)
        if old != EXPECTED_OLD:
            raise RuntimeError(
                f"{label}: expected {EXPECTED_OLD.hex()} at offset 0x{offset:08x}, "
                f"found {old.hex()}; refusing to patch"
            )
        fp.seek(offset)
        fp.write(NEW_BYTES)
    print(f"{label}: patched 0x{offset:08x} (VA 0x{offset+0x10000:08x}) to point at 0x{CAVE_VA:08x}")


def write_cave() -> None:
    with open(APP, "r+b") as fp:
        fp.seek(CAVE_FILE_OFFSET)
        before = fp.read(len(CAVE_STRING))
        if any(before):
            print(f"WARNING: cave at file offset 0x{CAVE_FILE_OFFSET:08x} was not zero-filled before write", file=sys.stderr)
        fp.seek(CAVE_FILE_OFFSET)
        fp.write(CAVE_STRING)
    print(f"wrote cave string {CAVE_STRING!r} at file offset 0x{CAVE_FILE_OFFSET:08x} (VA 0x{CAVE_VA:08x})")


if __name__ == "__main__":
    patch_movw_movt("udp_discovery", UDP_VERSION_PTR)
    patch_movw_movt("ws_attributes", WS_VERSION_PTR)
    patch_movw_movt("req_attribute", REQ_VERSION_PTR)
    write_cave()
