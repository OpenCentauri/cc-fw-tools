#!/usr/bin/env python3
"""Generate the CC1 1.4.46 TEMPERATURE_WAIT chamber/box patched app binary.

This rebuild relocates the 1.4.46 trampoline away from 0x00450100, which is
owned by fix-noncanvas-load. The old 1.4.46 temp-wait patch and
fix-noncanvas-load both used the same cave; when both were enabled, the later
patch overwrote the temp-wait target and the TEMPERATURE_WAIT handler returned
through corrupted control flow.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path

BASE_VADDR = 0x00010000
EXPECTED_SIZE = 4_787_332
EXPECTED_SHA256 = "ae693f7dc096da1f734c2972694963286cba20dc8f6afac79f8468139b613129"

HOOK_VA = 0x00177BC8
TRAMPOLINE_VA = 0x00450200
TRAMPOLINE_SIZE = 0xD8
CAVE_CHECK_SIZE = 0x100

# Rebuilt 1.4.46 trampoline. This is the previous 0x00450100 trampoline body,
# relocated to 0x00450200. All internal branches are PC-relative, so relocating
# as a block preserves their local targets. Absolute calls/returns remain valid:
# - sub_2b83c @ 0x0002b83c
# - usleep   @ 0x0001c514
# - stock epilogue resume @ 0x00177dd8
TRAMPOLINE = bytes.fromhex(
    "e0d04de234bb8ded36cb8dedf0009de50010d0e5620051e32a00001a"
    "0110d0e56f0051e32700001a0210d0e5780051e32400001a0310d0e5"
    "000051e32100001ae40c02e3440040e30010a0e30020a0e30d30a0e1"
    "3cc80be302c040e33cff2fe1000050e31100001a128b9ded34bb9ded"
    "36cb9dede0d08de2c8bbb4ee10faf1ee0500008ac8cbb4ee10faf1e"
    "e020000bad8cd07e317c040e31cff2fe1100702e314c50ce301c040e3"
    "3cff2fe1d3ffffeae0d08de2100702e314c50ce301c040e33cff2fe1"
    "cdffffeae0d08de2d8cd07e317c040e31cff2fe1"
)


def u32(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def va_to_off(va: int) -> int:
    return va - BASE_VADDR


def arm_b(src_va: int, dst_va: int, cond: int = 0xE) -> int:
    """Encode ARM B from src_va to dst_va."""
    # ARM branch offset is signed word offset from PC (current instruction + 8).
    delta = dst_va - (src_va + 8)
    if delta % 4:
        raise ValueError(f"Unaligned branch {src_va:#x} -> {dst_va:#x}")
    imm24 = (delta // 4) & 0x00FFFFFF
    return (cond << 28) | 0x0A000000 | imm24


def patch_word(buf: bytearray, va: int, word: int, expected: bytes | None = None) -> None:
    off = va_to_off(va)
    found = bytes(buf[off:off + 4])
    if expected is not None and found != expected:
        raise SystemExit(
            f"Refusing to patch {va:#x}: expected {expected.hex()}, found {found.hex()}"
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

    if len(TRAMPOLINE) != TRAMPOLINE_SIZE:
        raise SystemExit(f"Internal error: trampoline is {len(TRAMPOLINE)} bytes, expected {TRAMPOLINE_SIZE}")

    cave_off = va_to_off(TRAMPOLINE_VA)
    if bytes(data[cave_off:cave_off + CAVE_CHECK_SIZE]) != b"\0" * CAVE_CHECK_SIZE:
        raise SystemExit(f"Code cave at {TRAMPOLINE_VA:#x} is not empty; refusing to patch")

    data[cave_off:cave_off + len(TRAMPOLINE)] = TRAMPOLINE

    # Stock 1.4.46 at 0x177bc8:
    #   bl 0x000ed718
    # Replace with:
    #   b  0x00450200
    patch_word(
        data,
        HOOK_VA,
        arm_b(HOOK_VA, TRAMPOLINE_VA),
        expected=u32(0xEBFDD6D2),
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
