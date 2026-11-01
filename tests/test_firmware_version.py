#!/usr/bin/env python3
"""Version string written into app/app by the set-firmware-version patch."""
from pathlib import Path
import os
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "TOOLS"))

from firmware_version import firmware_version  # noqa: E402

CLEAN = {"OC_BUILD_BRANCH": "", "OC_BUILD_COMMIT": "", "OC_VERSION": "", "GITHUB_REF_NAME": ""}


def version(**env):
    with mock.patch.dict(os.environ, {**CLEAN, **env}, clear=False):
        return firmware_version(str(ROOT))


class FirmwareVersionTests(unittest.TestCase):
    def test_declared_release_version_wins(self):
        self.assertEqual(version(OC_VERSION="0.5.1"), "0.5.1-oc")
        self.assertEqual(version(OC_VERSION="v0.5.1"), "0.5.1-oc")

    def test_integrate_branch_beta_still_wins_over_declared_version(self):
        self.assertEqual(version(OC_BUILD_BRANCH="v0.5.1-integrate", OC_BUILD_COMMIT="abcdef1234",
                                 OC_VERSION="0.5.1"), "0.5.1-beta-abcdef1-oc")

    def test_invalid_declared_version_is_rejected(self):
        with self.assertRaises(ValueError):
            version(OC_VERSION="0.5")
        with self.assertRaises(ValueError):
            version(OC_VERSION="latest")

    def test_edition_config_declares_the_release_version(self):
        config = (ROOT / "firmware-editions/patched").read_text().splitlines()
        declared = [line for line in config if line.startswith("OC_VERSION=")]
        self.assertEqual(declared, ["OC_VERSION='0.5.1'"])


if __name__ == "__main__":
    unittest.main()
