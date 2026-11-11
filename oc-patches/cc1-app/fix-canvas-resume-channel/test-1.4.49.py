#!/usr/bin/env python3
"""Execute the real M6211/Resume ARM blocks; no printer or hardware access."""

import argparse
import itertools
import struct
from pathlib import Path

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_R0,
    UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R4, UC_ARM_REG_R5,
    UC_ARM_REG_R7, UC_ARM_REG_R10, UC_ARM_REG_R11,
)

from patch import BASE_VA, CAVE_VA, HOOK_NEW, HOOK_VA, REGIONS, TRAMPOLINE, patch_app

GLOBAL, PRINTER, MULTI = 0x10000000, 0x10001000, 0x10002000
STATE, CHANNEL, STACK, STOP = 0x10003000, 0x10004000, 0x20010000, 0x600000


def replay(app: bytes, tool: int, selected: int, active: int, previous: int) -> dict:
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(BASE_VA, 0x600000)
    uc.mem_write(BASE_VA, app)
    uc.mem_map(0x10000000, 0x100000)
    uc.mem_map(0x20000000, 0x20000)

    def write_word(address, value):
        uc.mem_write(address, struct.pack("<I", value & 0xFFFFFFFF))

    def read_word(address):
        return struct.unpack("<i", uc.mem_read(address, 4))[0]

    def return_from_stub(value=0):
        uc.reg_write(UC_ARM_REG_R0, value)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    for address, value in (
        (GLOBAL, PRINTER), (PRINTER + 0x22C, MULTI),
        (PRINTER + 0x230, 0x10005000), (PRINTER + 0xF8, 0x10006000),
        (PRINTER + 0xE4, 0x10007000), (MULTI + 0x4C, STATE),
        (MULTI + 0x44, CHANNEL), (STATE, 0x4451C4), (STATE + 0x44, previous),
    ):
        write_word(address, value)
    trace = {"fast_path": False, "setter_calls": 0}

    def hook(uc, address, size, user_data):
        # Logging, mutexes, filament checking and print-status reporting only.
        if address in (0x1B284, 0x1C52C, 0x2CFB90, 0x15ADF0, 0x1C78AC):
            return_from_stub()
        elif address == 0x515C4:
            return_from_stub(PRINTER)
        elif address == 0x29124C:
            # Substitute the file's mapping table, not the state-update logic.
            assert uc.reg_read(UC_ARM_REG_R2) == tool
            output = uc.reg_read(UC_ARM_REG_R0)
            uc.mem_write(output, bytes(36))
            write_word(output + 4, selected)
            return_from_stub(output)
        elif address == 0x293334:
            output = uc.reg_read(UC_ARM_REG_R0)
            uc.mem_write(output, bytes(36))
            write_word(output + 4, active)
            return_from_stub(output)
        elif address == 0x2794C8:
            trace["fast_path"] = True
        elif address == 0x278D64:
            # Normal path: omit fan/heater preparation before the real setter.
            uc.reg_write(UC_ARM_REG_PC, 0x278D9C)
        elif address == 0x2ADC68:
            trace["setter_calls"] += 1
        elif address in (0x279098, 0x278DB0):
            uc.emu_stop()  # Before stack teardown or physical load operations.
        elif address == 0x50BC0:
            pointer = uc.reg_read(UC_ARM_REG_R1)
            fmt = bytes(uc.mem_read(pointer, 64)).split(b"\0")[0]
            assert fmt == b"MULTICOLOR_RESUME CHANNEL_ID=%d"
            trace["resume_channel"] = struct.unpack(
                "<i", struct.pack("<I", uc.reg_read(UC_ARM_REG_R2))
            )[0]
            uc.emu_stop()

    uc.hook_add(UC_HOOK_CODE, hook)
    for reg, value in (
        (UC_ARM_REG_SP, STACK), (UC_ARM_REG_LR, STOP),
        (UC_ARM_REG_R4, STACK + 0x78), (UC_ARM_REG_R7, tool),
        (UC_ARM_REG_R10, GLOBAL), (UC_ARM_REG_R11, MULTI),
    ):
        uc.reg_write(reg, value)
    # Parameters are already parsed. Execute real mapping/state/branch code.
    uc.emu_start(0x278CC4, STOP, count=2000)
    trace["current_channel"] = read_word(STATE + 0x44)
    assert read_word(STATE + 0x48) == selected
    assert read_word(STATE + 0x4C) == tool
    for reg, value in (
        (UC_ARM_REG_SP, STACK), (UC_ARM_REG_R4, STACK + 0x78),
        (UC_ARM_REG_R5, selected), (UC_ARM_REG_R7, tool),
        (UC_ARM_REG_R10, GLOBAL), (UC_ARM_REG_R11, MULTI),
    ):
        assert uc.reg_read(reg) == value, (hex(reg), uc.reg_read(reg), value)
    uc.reg_write(UC_ARM_REG_SP, STACK)
    uc.reg_write(UC_ARM_REG_LR, STOP)
    # Execute the real getter/vtable dispatch and Resume command formatting.
    uc.emu_start(0x1B66D8, STOP, count=2000)
    assert trace.get("resume_channel") == trace["current_channel"]
    return trace


def check_rejections(original: bytes) -> None:
    cases = [(original, "1.4.46"), (original[:-1], "1.4.49")]
    for address, _, _ in REGIONS:
        damaged = bytearray(original)
        damaged[address - BASE_VA] ^= 1
        cases.append((bytes(damaged), "1.4.49"))
    occupied = bytearray(original)
    occupied[CAVE_VA - BASE_VA] = 1
    cases.extend([(bytes(occupied), "1.4.49"), (patch_app(original), "1.4.49")])
    for data, version in cases:
        before = bytes(data)
        try:
            patch_app(data, version)
        except ValueError:
            assert data == before
        else:
            raise AssertionError("Unsafe input was accepted")
    print(f"PASS: {len(cases)} incompatible/modified/occupied/repeated inputs refused")


def check_write_scope(original: bytes, patched: bytes) -> None:
    hook, cave = HOOK_VA - BASE_VA, CAVE_VA - BASE_VA
    assert len(patched) == len(original)
    assert patched[hook:hook + 4] == HOOK_NEW
    assert patched[cave:cave + 24] == TRAMPOLINE
    assert original[:hook] == patched[:hook]
    assert original[hook + 4:cave] == patched[hook + 4:cave]
    assert original[cave + 24:] == patched[cave + 24:]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path, help="unmodified stock 1.4.49 or OC v0.5.0 app")
    parser.add_argument("--patched-app", type=Path, help="also test the final full-chain app")
    args = parser.parse_args()
    original = args.app.read_bytes()
    patched = patch_app(original)
    check_write_scope(original, patched)
    check_rejections(original)
    candidates = [("isolated patch", patched)]
    if args.patched_app:
        final = args.patched_app.read_bytes()
        hook, cave = HOOK_VA - BASE_VA, CAVE_VA - BASE_VA
        assert final[hook:hook + 4] == HOOK_NEW
        assert final[cave:cave + 24] == TRAMPOLINE
        candidates.append(("full-chain app", final))

    stale = 0
    parameters = list(itertools.product(range(4), range(4), range(4), (-1, 0, 1, 2, 3)))
    for tool, selected, active, previous in parameters:
        before = replay(original, tool, selected, active, previous)
        assert before["current_channel"] == (previous if selected == active else selected)
        assert before["setter_calls"] == (0 if selected == active else 1)
        stale += selected == active and previous != selected
        for label, candidate in candidates:
            after = replay(candidate, tool, selected, active, previous)
            assert after["fast_path"] == before["fast_path"], (label, tool, selected, active, previous)
            assert after["current_channel"] == selected, (label, tool, selected, active, previous)
            assert after["resume_channel"] == selected, (label, tool, selected, active, previous)
            assert after["setter_calls"] == 1, (label, tool, selected, active, previous)
    print(f"BEFORE: reproduced {stale} stale/uninitialized already-loaded channel states")
    for label, _ in candidates:
        print(f"PASS: {len(parameters)} ARM selection/Resume cases for {label}")
    print("Hardware, heaters, sensor clearing and physical printing are not emulated.")


if __name__ == "__main__":
    main()
