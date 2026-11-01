#!/usr/bin/env python3
"""Regression for the CC1 1.4.49 SDCP firmware-version spoof.

Locks two contracts at once:
  * ElegooSlicer keeps seeing a version it recognises (a "1.4.49" prefix).
  * Home Assistant's elegoo_printer integration still recognises the firmware as
    OpenCentauri, so it creates the extrusion sensors Spoolman reads.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "oc-patches/cc1-app/spoof-slicer-firmware-version/patch.py"
STOCK = Path(os.environ.get("STOCK_APP", "/home/paul/carbon/cc-firmware/stock/app-1.4.49"))
SITES = (0x00359974, 0x0035bd64, 0x0036fbe4)
CAVE = 0x004417e0
VERSION_STRING = 0x003FAE10
SITE_BYTES = bytes.fromhex("e03701e3453040e3")


def run_patch(image, fw="1.4.49"):
    with tempfile.TemporaryDirectory(prefix="spoof-patch-") as directory:
        root = Path(directory)
        (root / "app").mkdir()
        target = root / "app/app"
        target.write_bytes(image)
        env = dict(os.environ, SQUASHFS_ROOT=str(root), FW_VER=fw)
        result = subprocess.run(["python3", str(PATCH)], env=env, capture_output=True, text=True)
        return result, target.read_bytes()


def is_open_centauri(model, firmware):
    """Mirror of elegoo_printer's Printer._is_open_centauri (SDCP firmware marker)."""
    import re
    if not model or not firmware:
        return False
    upper = firmware.upper()
    has_marker = bool(re.search(r"\bOC\b", upper) or re.search(r"\bO\b", upper)
                      or re.search(r"OC$", upper) or re.search(r"O$", upper))
    return "centauri" in model.lower() and has_marker


class SpoofSlicerVersionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock = STOCK.read_bytes()
        result, cls.patched = run_patch(cls.stock)
        if result.returncode:
            raise AssertionError(result.stderr + result.stdout)

    def test_three_sdcp_sites_repointed(self):
        for offset in SITES:
            self.assertEqual(self.patched[offset:offset + 8], SITE_BYTES, hex(offset))

    def test_real_version_string_untouched(self):
        self.assertEqual(self.patched[VERSION_STRING:VERSION_STRING + 8],
                         self.stock[VERSION_STRING:VERSION_STRING + 8])

    def test_cave_holds_slicer_prefix_and_oc_marker(self):
        raw = self.patched[CAVE:CAVE + 16].split(b"\0", 1)[0].decode("ascii")
        self.assertTrue(raw.startswith("1.4.49"), raw)
        # What the printer reports to SDCP clients is sprintf("V%s", cave).
        reported = "V" + raw
        self.assertTrue(is_open_centauri("Centauri Carbon", reported),
                        f"Home Assistant would not treat {reported!r} as OpenCentauri")
        self.assertFalse(is_open_centauri("Centauri Carbon", "V1.4.49"),
                         "guard: a bare stock version must not look like OpenCentauri")

    def test_cave_stays_clear_of_the_next_claim(self):
        # wait_for_chamber_temp owns 0x004517f0; the spoof string must end before it.
        self.assertLessEqual(CAVE + 16, 0x004417f0)

    def test_only_declared_regions_change(self):
        allowed = [(offset, 8) for offset in SITES] + [(CAVE, 11)]
        expected = bytearray(self.stock)
        for offset, size in allowed:
            expected[offset:offset + size] = self.patched[offset:offset + size]
        self.assertEqual(bytes(expected), self.patched)

    def test_guard_failures_are_non_mutating(self):
        for offset in list(SITES) + [CAVE]:
            with self.subTest(offset=hex(offset)):
                damaged = bytearray(self.stock)
                damaged[offset] ^= 1
                result, after = run_patch(bytes(damaged))
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(after, bytes(damaged))
        result, after = run_patch(self.stock, fw="1.4.46")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(after, self.stock)


if __name__ == "__main__":
    unittest.main()
