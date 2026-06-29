#!/usr/bin/env python3
"""Generate the CC1 1.4.46 fix-noncanvas-load patched app binary.

This script performs a small ARM32 trampoline patch against the stripped Elegoo
`/app/app` executable. It intentionally validates the exact original bytes so it
will fail closed on unknown firmware versions or already-mutated hook sites.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path

BASE_VADDR = 0x00010000
EXPECTED_SIZE = 4_787_332
EXPECTED_SHA256 = "ae693f7dc096da1f734c2972694963286cba20dc8f6afac79f8468139b613129"

# Executable zero-filled cave in the first RX PT_LOAD segment, inside .rodata.
# The first 128 bytes here are zero in the stock 1.4.46 app. We only need 72.
CODE_CAVE_VA = 0x00450100
CODE_CAVE_OFF = CODE_CAVE_VA - BASE_VADDR
CODE_CAVE_SIZE = 0x80

# ARM instruction helpers -----------------------------------------------------

def u32(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def arm_b(src_va: int, dst_va: int, cond: int = 0xE) -> int:
    """Encode an ARM-state B instruction from src_va to dst_va."""
    delta = dst_va - (src_va + 8)
    if delta % 4:
        raise ValueError(f"unaligned branch target: {src_va:#x} -> {dst_va:#x}")
    imm = delta // 4
    if not -(1 << 23) <= imm < (1 << 23):
        raise ValueError(f"branch target out of range: {src_va:#x} -> {dst_va:#x}")
    return (cond << 28) | 0x0A000000 | (imm & 0x00FFFFFF)


def arm_bl(src_va: int, dst_va: int) -> int:
    """Encode an ARM-state BL instruction from src_va to dst_va."""
    delta = dst_va - (src_va + 8)
    if delta % 4:
        raise ValueError(f"unaligned branch target: {src_va:#x} -> {dst_va:#x}")
    imm = delta // 4
    if not -(1 << 23) <= imm < (1 << 23):
        raise ValueError(f"branch target out of range: {src_va:#x} -> {dst_va:#x}")
    return 0xEB000000 | (imm & 0x00FFFFFF)


# Raw ARM opcodes used by the patch.
CMP_R0_0 = 0xE3500000
BXEQ_LR = 0x012FFF1E
PUSH_R4_R5_LR = 0xE92D4030
PUSH_R4_LR = 0xE92D4010
LDRB_R3_R0_0X3C = 0xE5D0303C
LDR_R0_R3_0X230 = 0xE5930230
MOV_R0_1 = 0xE3A00001
MOVEQ_R0_1 = 0x03A00001
NOP = 0xE320F000


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


def build_trampolines() -> bytes:
    pc = CODE_CAVE_VA
    words: list[int] = []

    def emit(word: int) -> None:
        nonlocal pc
        words.append(word)
        pc += 4

    # oc_guard_custom_filament_switch @ 0x450100
    # if r0 == NULL: return 0; else preserve overwritten push and resume sub_146378.
    emit(CMP_R0_0)                                   # 0x450100
    emit(BXEQ_LR)                                    # 0x450104
    emit(PUSH_R4_R5_LR)                              # 0x450108 original @ 0x146378
    emit(arm_b(pc, 0x0014637C))                      # 0x45010c

    # oc_guard_filament_wrap @ 0x450110
    emit(CMP_R0_0)                                   # 0x450110
    emit(BXEQ_LR)                                    # 0x450114
    emit(PUSH_R4_LR)                                 # 0x450118 original @ 0x15baa4
    emit(arm_b(pc, 0x0015BAA8))                      # 0x45011c

    # oc_guard_generic_switch @ 0x450120
    emit(CMP_R0_0)                                   # 0x450120
    emit(BXEQ_LR)                                    # 0x450124
    emit(LDRB_R3_R0_0X3C)                            # 0x450128 original @ 0x210fc8
    emit(arm_b(pc, 0x00210FCC))                      # 0x45012c

    # oc_load_final_filament_switch_guard @ 0x450130
    # Missing non-Canvas filament switch => synthesize low byte 1 only here.
    # Present Canvas filament switch => call original reader.
    emit(LDR_R0_R3_0X230)                            # 0x450130 original @ 0x13b12c
    emit(CMP_R0_0)                                   # 0x450134
    emit(MOVEQ_R0_1)                                 # 0x450138
    emit(arm_b(pc, 0x0013B134, cond=0x0))            # 0x45013c beq resume
    emit(arm_bl(pc, 0x00210FC8))                     # 0x450140 call guarded generic reader
    emit(arm_b(pc, 0x0013B134))                      # 0x450144 resume after original bl

    blob = b"".join(u32(w) for w in words)
    if len(blob) > CODE_CAVE_SIZE:
        raise AssertionError(f"trampolines too large: {len(blob)} > {CODE_CAVE_SIZE}")
    return blob


def patch_app(src: Path, dst: Path) -> None:
    data = bytearray(src.read_bytes())
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != EXPECTED_SIZE or digest != EXPECTED_SHA256:
        raise SystemExit(
            f"Unsupported source app. Expected size {EXPECTED_SIZE} sha256 {EXPECTED_SHA256}; "
            f"got size {len(data)} sha256 {digest}"
        )

    if bytes(data[CODE_CAVE_OFF:CODE_CAVE_OFF + CODE_CAVE_SIZE]) != b"\0" * CODE_CAVE_SIZE:
        raise SystemExit(f"Code cave at {CODE_CAVE_VA:#x} is not empty; refusing to patch")

    # Write trampolines first.
    tramp = build_trampolines()
    data[CODE_CAVE_OFF:CODE_CAVE_OFF + len(tramp)] = tramp

    # Branch hooks.
    patch_word(data, 0x00146378, arm_b(0x00146378, 0x00450100), bytes.fromhex("30402de9"))
    patch_word(data, 0x0015BAA4, arm_b(0x0015BAA4, 0x00450110), bytes.fromhex("10402de9"))
    patch_word(data, 0x00210FC8, arm_b(0x00210FC8, 0x00450120), bytes.fromhex("3c30d0e5"))

    # Replace final load-completion ldr/bl pair with trampoline branch + NOP.
    patch_word(data, 0x0013B12C, arm_b(0x0013B12C, 0x00450130), bytes.fromhex("300293e5"))
    patch_word(data, 0x0013B130, NOP, bytes.fromhex("a45703eb"))

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
