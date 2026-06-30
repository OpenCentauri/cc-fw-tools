#!/usr/bin/env python3
"""Generate the CC1 1.4.46 fix-m600-pause patched app binary.

This patch hooks the M600 handler's end-of-unload event dispatch so the hotend
is kept warm after CUT_OFF_FILAMENT turns it off. It queues:

    M104 S200

right before the handler dispatches the resume / change-filament-completed
event (0x1a). This prevents the UI from getting stuck waiting for a hotend that
has dropped to 0 °C and never receives a temperature command.

The patch is generated against the pre-FIX_M600_PAUSE intermediate app in the
patch_planner order, not against the raw stock app. It validates exact
hook/cave bytes before writing anything.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path

BASE_VADDR = 0x00010000
EXPECTED_SIZE = 4_787_332

# Hook the BL to sub_1c7908() at the end of PauseResume::cmd_M600.
HOOK_VA = 0x001B84C4
RESUME_VA = 0x001B84C8  # instruction after the original BL

# Code cave immediately after the fix-end-print-hang reserved area.
CODE_CAVE_VA = 0x00450D00
CODE_CAVE_SIZE = 0x80

# String cave just after the fix-end-print-hang string cave.
STRING_VA = 0x00450C40
STRING_SIZE = 0x40
COMMAND = b"M104 S200\0"

# Original instruction at the hook: bl sub_1c7908
ORIG_HOOK = bytes.fromhex("0f 3d 00 eb")


def u32(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def va_to_off(va: int) -> int:
    return va - BASE_VADDR


def arm_b(src_va: int, dst_va: int, cond: int = 0xE) -> int:
    delta = dst_va - (src_va + 8)
    if delta % 4:
        raise ValueError(f"unaligned branch target: {src_va:#x} -> {dst_va:#x}")
    imm = delta // 4
    if not -(1 << 23) <= imm < (1 << 23):
        raise ValueError(f"branch target out of range: {src_va:#x} -> {dst_va:#x}")
    return (cond << 28) | 0x0A000000 | (imm & 0x00FFFFFF)


def arm_bl(src_va: int, dst_va: int) -> int:
    delta = dst_va - (src_va + 8)
    if delta % 4:
        raise ValueError(f"unaligned branch target: {src_va:#x} -> {dst_va:#x}")
    imm = delta // 4
    if not -(1 << 23) <= imm < (1 << 23):
        raise ValueError(f"branch target out of range: {src_va:#x} -> {dst_va:#x}")
    return 0xEB000000 | (imm & 0x00FFFFFF)


def arm_movw(reg: int, imm16: int, cond: int = 0xE) -> int:
    return (
        (cond << 28)
        | 0x03000000
        | ((imm16 & 0xF000) << 4)
        | (reg << 12)
        | (imm16 & 0x0FFF)
    )


def arm_movt(reg: int, imm16: int, cond: int = 0xE) -> int:
    return (
        (cond << 28)
        | 0x03400000
        | ((imm16 & 0xF000) << 4)
        | (reg << 12)
        | (imm16 & 0x0FFF)
    )


# ARM opcodes used by the trampoline.
PUSH_R0_R3_IP_LR = 0xE92D500F  # push {r0, r1, r2, r3, ip, lr}
POP_R0_R3_IP_LR = 0xE8BD500F  # pop {r0, r1, r2, r3, ip, lr}
LDR_R0_R0_0 = 0xE5900000
LDR_R0_R0_0XE4 = 0xE59000E4
CMP_R0_0 = 0xE3500000
MOV_R2_0 = 0xE3A02000


def build_trampoline() -> bytes:
    pc = CODE_CAVE_VA
    words: list[int] = []

    def emit(word: int) -> None:
        nonlocal pc
        words.append(word)
        pc += 4

    emit(PUSH_R0_R3_IP_LR)                    # preserve r0-r3, ip, lr
    emit(arm_movw(0, 0x1034))                 # r0 = &data_4b1034
    emit(arm_movt(0, 0x004B))
    emit(LDR_R0_R0_0)                         # r0 = data_4b1034
    emit(CMP_R0_0)
    restore_beq_1_pc = pc
    emit(0)                                   # beq .Lrestore, filled later
    emit(LDR_R0_R0_0XE4)                      # r0 = data_4b1034[0x39] (gcode object)
    emit(CMP_R0_0)
    restore_beq_2_pc = pc
    emit(0)                                   # beq .Lrestore, filled later
    emit(arm_movw(1, STRING_VA & 0xFFFF))     # r1 = command string
    emit(arm_movt(1, STRING_VA >> 16))
    emit(MOV_R2_0)                            # r2 = 0
    emit(arm_bl(pc, 0x00050B88))              # sub_50b88(gcode_obj, command, 0)
    restore_va = pc
    emit(POP_R0_R3_IP_LR)                     # restore registers
    emit(arm_b(pc, 0x001C7908))               # tail-call original sub_1c7908

    # Patch the two conditional branches to jump to .Lrestore if data is missing.
    words[(restore_beq_1_pc - CODE_CAVE_VA) // 4] = arm_b(restore_beq_1_pc, restore_va, cond=0x0)
    words[(restore_beq_2_pc - CODE_CAVE_VA) // 4] = arm_b(restore_beq_2_pc, restore_va, cond=0x0)

    blob = b"".join(u32(w) for w in words)
    if len(blob) > CODE_CAVE_SIZE:
        raise AssertionError(f"trampoline too large: {len(blob)} > {CODE_CAVE_SIZE}")
    return blob


def patch_app(src: Path, dst: Path) -> None:
    data = bytearray(src.read_bytes())
    if len(data) != EXPECTED_SIZE:
        raise SystemExit(f"Unexpected app size {len(data)}; expected {EXPECTED_SIZE}")

    hook_off = va_to_off(HOOK_VA)
    if bytes(data[hook_off:hook_off + 4]) != ORIG_HOOK:
        raise SystemExit(
            f"Refusing to patch hook {HOOK_VA:#x}: got "
            f"{bytes(data[hook_off:hook_off + 4]).hex(' ')}, want {ORIG_HOOK.hex(' ')}"
        )

    cave_off = va_to_off(CODE_CAVE_VA)
    if bytes(data[cave_off:cave_off + CODE_CAVE_SIZE]) != b"\0" * CODE_CAVE_SIZE:
        raise SystemExit(f"Code cave {CODE_CAVE_VA:#x}-{CODE_CAVE_VA + CODE_CAVE_SIZE - 1:#x} is not empty")

    string_off = va_to_off(STRING_VA)
    if bytes(data[string_off:string_off + STRING_SIZE]) != b"\0" * STRING_SIZE:
        raise SystemExit(f"String cave {STRING_VA:#x}-{STRING_VA + STRING_SIZE - 1:#x} is not empty")

    trampoline = build_trampoline()
    data[cave_off:cave_off + len(trampoline)] = trampoline
    data[string_off:string_off + len(COMMAND)] = COMMAND
    data[hook_off:hook_off + 4] = u32(arm_b(HOOK_VA, CODE_CAVE_VA))

    dst.write_bytes(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=Path, help="pre-FIX_M600_PAUSE app binary")
    parser.add_argument("dst", type=Path, help="output patched app binary")
    args = parser.parse_args()
    patch_app(args.src, args.dst)
    print(f"wrote {args.dst}")
    print(f"sha256 {hashlib.sha256(args.dst.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
