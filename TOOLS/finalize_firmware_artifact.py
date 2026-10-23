#!/usr/bin/env python3
"""Give the final firmware image a manifest-derived artifact filename."""

import argparse
import hashlib
import json
import os
import re
from datetime import datetime


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_filename_part(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._+-]+", "-", value).strip(".-")
    if not value:
        raise SystemExit("Error: manifest produced an empty filename component")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--firmware", required=True, help="Current final firmware path")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    with open(args.manifest, encoding="utf-8") as file:
        manifest = json.load(file)

    build = manifest.get("build", {})
    completed_at = build.get("completed_at")
    if not completed_at:
        raise SystemExit("Error: manifest is missing build.completed_at")

    try:
        completed = datetime.strptime(completed_at, "%Y-%m-%d %H:%M:%S UTC")
    except ValueError as error:
        raise SystemExit(
            "Error: build.completed_at must use YYYY-MM-DD HH:MM:SS UTC"
        ) from error

    firmware_version = build.get("firmware_version") or build.get("version")
    if not firmware_version:
        raise SystemExit("Error: manifest is missing build.firmware_version and build.version")

    timestamp = completed.strftime("%Y-%m-%d-%H%M%S")
    filename = f"update-{timestamp}_{safe_filename_part(firmware_version)}.swu"
    output_path = os.path.join(args.output_dir, filename)

    if not os.path.isfile(args.firmware):
        raise SystemExit(f"Error: firmware file not found: {args.firmware}")

    expected_sha256 = manifest.get("final_firmware", {}).get("sha256")
    actual_sha256 = sha256(args.firmware)
    if expected_sha256 and actual_sha256 != expected_sha256:
        raise SystemExit(
            "Error: firmware SHA-256 does not match manifest before renaming "
            f"({actual_sha256} != {expected_sha256})"
        )

    os.replace(args.firmware, output_path)

    final_firmware = manifest.setdefault("final_firmware", {})
    final_firmware["file_name"] = filename
    final_firmware["path"] = output_path

    with open(args.manifest, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)
        file.write("\n")

    print(f"Final firmware artifact: {output_path}")


if __name__ == "__main__":
    main()
