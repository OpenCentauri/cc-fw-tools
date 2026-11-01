#!/usr/bin/env python3
"""Machine-code regression for the CC1 1.4.49 filament-reporting port."""
import ast
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_CPU_ARM_CORTEX_A7, UC_ARM_REG_C1_C0_2, UC_ARM_REG_FPEXC,
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
    UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11,
    UC_ARM_REG_R12, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
    UC_ARM_REG_D0, UC_ARM_REG_D8,
)

ROOT = Path(__file__).resolve().parents[1]
PATCH_DIR = ROOT / "oc-patches/cc1-app/report-filament-usage"
STOCK = Path(os.environ.get("STOCK_APP", "/home/paul/carbon/cc-firmware/stock/app-1.4.49"))
ORIGINAL_STOCK = Path(os.environ.get("ORIGINAL_STOCK_APP", "/home/paul/carbon/cc-firmware/stock/app-1.1.40"))
HEX_TOTAL = "54 6F 74 61 6C 45 78 74 72 75 73 69 6F 6E 00"
HEX_DELTA = "43 75 72 72 65 6E 74 45 78 74 72 75 73 69 6F 6E 00"
REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
        UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
        UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11)
ELF_EDITS = ((0xc8, 0x741fc, 0x74210),
             (0x492380, 0x710d4, 0x710e8),
             (0x1724, 0x522f04, 0x522f18),
             (0x20a4, 0x522f04, 0x522f18),
             (0x3e34, 0x522f04, 0x522f18),
             (0x4044, 0x522f04, 0x522f18))


def run_patch(image, fw="1.4.49"):
    with tempfile.TemporaryDirectory(prefix="filament-patch-") as directory:
        root = Path(directory)
        (root / "app").mkdir()
        target = root / "app/app"
        target.write_bytes(image)
        env = dict(os.environ, SQUASHFS_ROOT=str(root), FW_VER=fw)
        result = subprocess.run(["python3", str(PATCH_DIR / "patch.py")],
                                env=env, capture_output=True, text=True)
        return result, target.read_bytes()


def emissions(image, old=False):
    """Execute only the real hook/cave; stub the native JSON-number helper."""
    entry, resume, helper, singleton, low_key = (
        (0x2deb18, 0x2deb28, 0x268720, 0x3e54d4, 0x6724) if old else
        (0x36d310, 0x36d320, 0x2c9b80, 0x4b27bc, 0x96d0))
    mu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    mu.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A7)
    mu.reg_write(UC_ARM_REG_C1_C0_2, 0xf << 20)
    mu.reg_write(UC_ARM_REG_FPEXC, 1 << 30)
    mu.mem_map(0x10000, 0x530000)
    phoff = struct.unpack_from("<I", image, 28)[0]
    phents, phnum = struct.unpack_from("<HH", image, 42)
    for index in range(phnum):
        kind, off, va, _, filesz, _, _, _ = struct.unpack_from("<8I", image, phoff + index * phents)
        if kind == 1:
            mu.mem_write(va, image[off:off + filesz])
    # Anonymous mappings start zeroed, just as the new ELF BSS allocation must.
    mu.mem_map(0x1000000, 0x4000)
    mu.mem_map(0x2000000, 0x4000)
    printer, stats, json_object = 0x1000000, 0x1001000, 0x1002000
    mu.mem_write(singleton, struct.pack("<I", printer))
    mu.mem_write(printer + 0xf8, struct.pack("<I", stats))
    prng = bytes(range(256)) * 9 + bytes(range(192))
    if not old:
        mu.mem_write(0x4b45f0, prng)
    records = []

    def json_helper(uc, address, size, user_data):
        pointer = uc.reg_read(UC_ARM_REG_R1)
        key = bytes(uc.mem_read(pointer, 128)).split(b"\0", 1)[0].decode("ascii")
        value = struct.unpack("<d", struct.pack("<Q", uc.reg_read(UC_ARM_REG_D0)))[0]
        records.append((uc.reg_read(UC_ARM_REG_R0), key, value))
        return_pc = uc.reg_read(UC_ARM_REG_LR)
        for reg in (*REGS[:4], UC_ARM_REG_R12):
            uc.reg_write(reg, 0xdead0000)
        for index in range(8):
            uc.reg_write(UC_ARM_REG_D0 + index, 0)
        uc.reg_write(UC_ARM_REG_PC, return_pc)

    mu.hook_add(UC_HOOK_CODE, json_helper, begin=helper, end=helper)
    output = []
    for total in (0.0, 10.0, 7.0, 12.0, 0.0):
        mu.mem_write(stats + 0x1c0, struct.pack("<d", total))
        for index, reg in enumerate(REGS):
            mu.reg_write(reg, 0x1003000 + index * 16)
        mu.reg_write(UC_ARM_REG_R0, json_object)
        mu.reg_write(UC_ARM_REG_R1, low_key)
        mu.reg_write(UC_ARM_REG_R3, 17)
        mu.reg_write(UC_ARM_REG_R8, json_object)
        mu.reg_write(UC_ARM_REG_SP, 0x2003f00)
        for index in range(8):
            mu.reg_write(UC_ARM_REG_D8 + index, 0x1122334400000000 + index)
        before = [mu.reg_read(reg) for reg in (*REGS, UC_ARM_REG_SP)]
        fp_before = [mu.reg_read(UC_ARM_REG_D8 + index) for index in range(8)]
        records.clear()
        mu.emu_start(entry, resume, count=200)
        if mu.reg_read(UC_ARM_REG_PC) != resume:
            raise AssertionError("trampoline did not reach the stock continuation")
        if [mu.reg_read(reg) for reg in (*REGS, UC_ARM_REG_SP)] != before:
            raise AssertionError("trampoline clobbered a preserved register or SP")
        if [mu.reg_read(UC_ARM_REG_D8 + index) for index in range(8)] != fp_before:
            raise AssertionError("trampoline clobbered callee-saved VFP registers")
        if len(records) != 3 or any(obj != json_object for obj, _, _ in records):
            raise AssertionError("expected TotalLayer and two usage fields on r8 JSON object")
        values = {key: value for _, key, value in records}
        output.append((values["TotalLayer"],
                       values.get("TotalExtrusion", values.get(HEX_TOTAL)),
                       values.get("CurrentExtrusion", values.get(HEX_DELTA))))
        if not old and bytes(mu.mem_read(0x4b45f0, len(prng))) != prng:
            raise AssertionError("filament reporting overwrote stock PRNG state")
    return output


class FilamentReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock = STOCK.read_bytes()
        if hashlib.sha256(cls.stock).hexdigest() != "1a899b50fc104a38fe3f77cf4988c810da6670f3d0cc457de5d876c49fd76843":
            raise AssertionError("wrong stock 1.4.49 fixture")
        result, cls.patched = run_patch(cls.stock)
        if result.returncode:
            raise AssertionError(result.stderr + result.stdout)

    def test_broadcast_hook_and_unmodified_agora(self):
        self.assertEqual(self.patched[0x35d310:0x35d31c], bytes.fromhex("d0c801e345c040e31cff2fe1"))
        self.assertEqual(self.patched[0x36f9ec:0x36f9ff], self.stock[0x36f9ec:0x36f9ff])

    def test_explicit_elf_reservation(self):
        images = [self.patched]
        if candidate := os.environ.get("PATCHED_APP"):
            images.append(Path(candidate).read_bytes())
        for offset, old, new in ELF_EDITS:
            self.assertEqual(struct.unpack_from("<I", self.stock, offset)[0], old)
            for image in images:
                self.assertEqual(struct.unpack_from("<I", image, offset)[0], new)
        for image in images:
            self.assertEqual(len(image), len(self.stock))

    def test_only_declared_regions_change(self):
        allowed = [(0x35d310, 12), (0x4418d0, 196),
                   (0x4419a0, 15), (0x4419b0, 17)]
        allowed.extend((offset, 4) for offset, _, _ in ELF_EDITS)
        expected = bytearray(self.stock)
        for offset, size in allowed:
            expected[offset:offset + size] = self.patched[offset:offset + size]
        self.assertEqual(bytes(expected), self.patched)

    def test_guard_failures_are_non_mutating(self):
        offsets = [0x35d30c, 0x35d310, 0x35d31c, 0x4418d0, 0x4419a0, 0x4419b0]
        offsets.extend(offset for offset, _, _ in ELF_EDITS)
        for offset in offsets:
            with self.subTest(offset=hex(offset)):
                damaged = bytearray(self.stock)
                damaged[offset] ^= 1
                result, after = run_patch(bytes(damaged))
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(after, bytes(damaged))
        result, after = run_patch(self.patched)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(after, self.patched)
        result, after = run_patch(self.stock, fw="1.4.46")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(after, self.stock)
        result, after = run_patch(self.stock[:-1])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(after, self.stock[:-1])

    def test_assembly_matches_embedded_blob(self):
        values = {}
        for node in ast.parse((PATCH_DIR / "patch.py").read_text()).body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                try:
                    values[node.targets[0].id] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    pass
        with tempfile.TemporaryDirectory(prefix="filament-asm-") as directory:
            tmp = Path(directory)
            subprocess.run(["arm-linux-gnueabihf-as", "-march=armv7-a", "-mfpu=vfpv3", "-o", str(tmp / "fn.o"), str(PATCH_DIR / "injected-1.4.49.S")], check=True)
            subprocess.run(["arm-linux-gnueabihf-ld", "-Ttext=0x4518d0", "-o", str(tmp / "fn.elf"), str(tmp / "fn.o")], check=True)
            subprocess.run(["arm-linux-gnueabihf-objcopy", "-O", "binary", "-j", ".text", str(tmp / "fn.elf"), str(tmp / "fn.bin")], check=True)
            self.assertEqual((tmp / "fn.bin").read_bytes(), bytes.fromhex(values["FN"]))
            self.assertEqual(len((tmp / "fn.bin").read_bytes()), 196)

    def test_machine_code_matches_original_signed_contract(self):
        raw = ORIGINAL_STOCK.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), "6d7431a1a55c430b70e30137eacd1055c40be392f65a51c307b78f58bded5999")
        with tempfile.TemporaryDirectory(prefix="filament-original-") as directory:
            original = Path(directory) / "app"
            subprocess.run(["bspatch", str(ORIGINAL_STOCK), str(original), str(PATCH_DIR / "report_filament_usage_patch-1.1.40.bsdiff")], check=True)
            expected = emissions(original.read_bytes(), old=True)
        self.assertEqual(expected, [(17.0, 0.0, 0.0), (17.0, 10.0, 10.0),
                                    (17.0, 7.0, -3.0), (17.0, 12.0, 5.0),
                                    (17.0, 0.0, -12.0)])
        self.assertEqual(emissions(self.patched), expected)
        candidate = os.environ.get("PATCHED_APP")
        if candidate:
            self.assertEqual(emissions(Path(candidate).read_bytes()), expected)


if __name__ == "__main__":
    unittest.main()
