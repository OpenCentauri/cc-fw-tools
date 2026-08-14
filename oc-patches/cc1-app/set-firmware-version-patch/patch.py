#!/usr/bin/python3

import os
import sys

SQUASHFS_ROOT = os.getenv("SQUASHFS_ROOT")
REPOSITORY_ROOT = os.getenv("REPOSITORY_ROOT")
FW_VER = os.getenv("FW_VER", "1.1.40")

if not SQUASHFS_ROOT:
    raise RuntimeError("SQUASHFS_ROOT environment variable is required")
if not REPOSITORY_ROOT:
    raise RuntimeError("REPOSITORY_ROOT environment variable is required")

sys.path.insert(0, os.path.join(REPOSITORY_ROOT, "TOOLS"))
from firmware_version import firmware_version

VERSION_OFFSETS = {
    "1.1.40": (0x34F6E8, b"1.1.40"),
    "1.4.46": (0x003F9A38, b"1.4.46"),
    "1.4.49": (0x003FAE10, b"1.4.49"),
}

try:
    version = firmware_version(REPOSITORY_ROOT)
except:
    version = "Unknown-oc"

version = version + "\0"
encoded = version.encode(encoding="ASCII")
print(version)

if FW_VER not in VERSION_OFFSETS:
    raise RuntimeError(f"Unsupported firmware version for set-firmware-version patch: {FW_VER}")

offset, expected_stock = VERSION_OFFSETS[FW_VER]
app_path = os.path.join(SQUASHFS_ROOT, "app", "app")
with open(app_path, "r+b") as fp:
    fp.seek(offset, os.SEEK_SET)
    existing = fp.read(len(expected_stock))
    if existing != expected_stock:
        raise RuntimeError(
            f"set-firmware-version patch for {FW_VER}: expected stock bytes {expected_stock!r} at offset 0x{offset:08x}, "
            f"but found {existing!r}. Refusing to overwrite."
        )
    fp.seek(offset, os.SEEK_SET)
    fp.write(encoded)
