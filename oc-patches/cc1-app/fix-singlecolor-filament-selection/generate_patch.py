#!/usr/bin/env python3
"""Generate the CC1 1.4.46 fix-singlecolor-filament-selection patched app binary.

This patch forces the SET_ALL_CHANNELS_SAME handler to always write 0,
which prevents cmd_M749 from skipping the unload/load cycle on single-color
prints. The printer will always respect the user-selected color.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path

BASE_VADDR = 0x00010000
EXPECTED_SIZE = 4_787_332
EXPECTED_SHA256 = "ae693f7dc096da1f734c2972694963286cba20dc8f6afac79f8468139b613129"


def u32(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def va_to_off(va: int) -> int:
    return va - BASE_VADDR


def patch_word(buf: bytearray, va: int, word: int, expected: bytes | None = None) -> None:
    off = va_to_off(va)
    if expected is not None and bytes(buf[off:off + 4]) != expected:
        raise SystemExit(
            f"Refusing to patch {va:#x}: expected {expected.hex()}, "
            f"found {bytes(buf[off:off + 4]).hex()}"
        )
    buf[off:off + 4] = u32(word)


def patch_app(src: Path, dst: Path) -> None:
    data = bytearray(src.read_bytes())
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != EXPECTED_SIZE or digest != EXPECTED_SHA256:
        raise SystemExit(
            f"Unsupported source app. Expected size {EXPECTED_SIZE} sha256 {EXPECTED_SHA256}; "
            f"got size {len(data)} sha256 {digest}"
        )

    # Patch sub_239698 (SET_ALL_CHANNELS_SAME handler):
    # Force the store to always write 0 instead of the parsed VALUE.
    #
    # Disassembly at 0x239714 (from objdump):
    #   239714: 13a00001  movne r0, #1
    #   239718: e3403043  movt  r3, #67
    #   23971c: e5c60214  strb  r0, [r6, #532]  ; 0x214
    #
    # r0 is the parsed VALUE (0 or non-zero). movne r0, #1 converts
    # non-zero to 1. We replace it with unconditional mov r0, #0 so
    # the following strb always stores 0, making all_channels_same
    # permanently false.
    patch_word(
        data,
        0x00239714,
        0xE3A00000,           # mov r0, #0  (was movne r0, #1)
        expected=u32(0x13A00001),
    )

    dst.write_bytes(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=Path, help="stock 1.4.46 app binary")
    parser.add_argument("dst", type=Path, help="output patched app binary")
    args = parser.parse_args()
    patch_app(args.src, args.dst)
    print(f"wrote {args.dst}")
    print(f"sha256 {hashlib.sha256(args.dst.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
