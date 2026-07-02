#!/usr/bin/env python3
"""Spoof the firmware version reported to ElegooSlicer in SDCP attribute responses.

Stock CC1 1.4.46 reads the version string from VA 0x00409a38 for:
- UDP discovery responses (sub_368528, VA 0x0036859c)
- WebSocket/MQTT attributes topic (sub_36a948, VA 0x0036a98c)
- Direct request-attribute responses (sub_37e730, VA 0x0037e80c)

This patch repoints the source pointer in all three functions to a new code cave at
VA 0x00450e00 containing a fixed "1.4.46\0" string. The original version string at
VA 0x00409a38 (logs, UI, OTA) is left untouched.
"""

import os
import sys

SQUASHFS_ROOT = os.getenv("SQUASHFS_ROOT")
FW_VER = os.getenv("FW_VER", "1.4.46")

if not SQUASHFS_ROOT:
    raise RuntimeError("SQUASHFS_ROOT environment variable is required")
if FW_VER != "1.4.46":
    raise RuntimeError(f"Unsupported firmware version for spoof-slicer-firmware-version patch: {FW_VER}")

APP = os.path.join(SQUASHFS_ROOT, "app", "app")

# File offsets (VA - 0x00010000, single LOAD segment starts at VA 0x10000/file 0).
UDP_VERSION_PTR = 0x0035859c      # VA 0x0036859c
WS_VERSION_PTR = 0x0035a98c       # VA 0x0036a98c
REQ_VERSION_PTR = 0x0036e80c      # VA 0x0037e80c (file offset = VA - 0x10000)
CAVE_VA = 0x00450e00              # chosen to avoid collision with fix-m600-pause cave
CAVE_FILE_OFFSET = CAVE_VA - 0x00010000

EXPECTED_OLD = bytes.fromhex("383a09e3403040e3")  # movw r3,#0x9a38; movt r3,#0x40
NEW_BYTES = bytes.fromhex("003e00e3453040e3")     # movw r3,#0x0e00; movt r3,#0x45
CAVE_STRING = b"1.4.46\x00"     # 7 bytes, matching the stock 7-byte version slot


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
    patch_movw_movt("ws_request_attr", WS_VERSION_PTR)
    patch_movw_movt("req_attribute", REQ_VERSION_PTR)
    write_cave()
