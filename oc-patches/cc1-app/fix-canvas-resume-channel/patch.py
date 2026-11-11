#!/usr/bin/env python3
"""Update the current physical channel on the M6211 already-loaded path."""

import hashlib
import os
import struct
from pathlib import Path

APP_SIZE = 4_793_356
BASE_VA = 0x10000
HOOK_VA = 0x278D60
CAVE_VA = 0x4519D0
CONTINUE_VA = 0x2794C8
HOOK_OLD = bytes.fromhex("d801000a")  # beq 0x2794c8

# Guard the handler, state accessors and virtual slots against ABI changes.
# Full-file hashes cannot be used because other patches run on the same app.
REGIONS = (
    (0x278594, 5100, "a71ad73ac51121d715f593d48963b112dc82eaea85a52419f20f52fb47ebf4f2"),
    (0x2AD588, 80, "9ba697be0681dcd2b73cbbd6be73090d5a2c3f47d079a76dc47abd956a181d9f"),
    (0x2ADC68, 164, "966e0b62180a620f6cf5c1b0b8c6ed39eb725e103fd3ac275dcd763f75e00a0a"),
    (0x4451C4, 104, "8ebb4451bd43857f2383eee39ed88256e40ed118ccde0b7d527d9262446fa104"),
)


def branch(source: int, target: int, condition: int = 0xE) -> bytes:
    delta = target - source - 8
    if delta % 4 or not -(1 << 25) <= delta < (1 << 25):
        raise ValueError("ARM branch target is unaligned or out of range")
    return struct.pack("<I", condition << 28 | 0x0A000000 | ((delta // 4) & 0xFFFFFF))


HOOK_NEW = branch(HOOK_VA, CAVE_VA, condition=0)  # Keep the existing EQ condition.
TRAMPOLINE = bytes.fromhex(
    "4c009be5"  # ldr r0, [r11, #0x4c]   ; MultiColorState*
    "0510a0e1"  # mov r1, r5              ; mapped physical channel
    "003090e5"  # ldr r3, [r0]
    "583093e5"  # ldr r3, [r3, #0x58]     ; set_current_print_channel_id
    "33ff2fe1"  # blx r3
) + branch(CAVE_VA + 20, CONTINUE_VA)


def patch_app(data: bytes, version: str = "1.4.49") -> bytes:
    if version != "1.4.49":
        raise ValueError(f"Unsupported firmware version: {version}")
    if len(data) != APP_SIZE:
        raise ValueError(f"Unsupported app size: {len(data)} (expected {APP_SIZE})")
    for address, size, expected in REGIONS:
        region = data[address - BASE_VA:address - BASE_VA + size]
        if hashlib.sha256(region).hexdigest() != expected:
            raise ValueError(f"Unexpected code/ABI at VA {address:#x}; refusing to patch")
    hook = HOOK_VA - BASE_VA
    cave = CAVE_VA - BASE_VA
    if data[hook:hook + 4] != HOOK_OLD:
        raise ValueError("Unexpected M6211 branch; refusing to patch")
    if any(data[cave:cave + len(TRAMPOLINE)]):
        raise ValueError(f"Code cave at VA {CAVE_VA:#x} is not empty; refusing to patch")
    result = bytearray(data)
    result[cave:cave + len(TRAMPOLINE)] = TRAMPOLINE
    result[hook:hook + 4] = HOOK_NEW
    return bytes(result)


def main() -> None:
    root = os.environ.get("SQUASHFS_ROOT")
    if not root:
        raise ValueError("SQUASHFS_ROOT environment variable is required")
    app = Path(root) / "app" / "app"
    # Validate every region before making any change to the file.
    result = patch_app(app.read_bytes(), os.environ.get("FW_VER", "1.4.49"))
    app.write_bytes(result)
    print(f"M6211 already-loaded hook: {HOOK_VA:#x} -> {CAVE_VA:#x}")
    print(f"Wrote {len(TRAMPOLINE)}-byte channel-state trampoline; continue at {CONTINUE_VA:#x}")


if __name__ == "__main__":
    main()
