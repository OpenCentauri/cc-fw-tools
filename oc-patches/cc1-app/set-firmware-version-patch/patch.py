#!/usr/bin/python3

import subprocess, os

SQUASHFS_ROOT = os.getenv("SQUASHFS_ROOT")
REPOSITORY_ROOT = os.getenv("REPOSITORY_ROOT")
FW_VER = os.getenv("FW_VER", "1.1.40")

if not SQUASHFS_ROOT:
    raise RuntimeError("SQUASHFS_ROOT environment variable is required")
if not REPOSITORY_ROOT:
    raise RuntimeError("REPOSITORY_ROOT environment variable is required")

VERSION_OFFSETS = {
    "1.1.40": (0x34F6E8, b"1.1.40"),
    "1.4.46": (0x003F9A38, b"1.4.46"),
}

def extract_commit() -> str:
    git_describe_output = subprocess.run(["git", "--git-dir", os.path.join(REPOSITORY_ROOT, ".git"), "describe", "--tags"], stdout=subprocess.PIPE, text=True, check=True).stdout.strip()
    split_output = git_describe_output.split("-")

    if (len(split_output) >= 3):
        version = f"{split_output[0]}-{split_output[2][1:]}"
    else:
        version = split_output[0]

    if version.startswith("v"):
        return version[1:]

    return version

try:
    version = extract_commit()
except:
    version = "Unknown"

version = version + "-oc\0"
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
