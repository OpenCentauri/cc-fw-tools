#!/usr/bin/env python3
"""Create a Markdown patch summary from a firmware manifest."""

import argparse
import json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.manifest, encoding="utf-8") as file:
        manifest = json.load(file)

    original = manifest["original_firmware"]
    final = manifest["final_firmware"]
    build = manifest["build"]
    patches = manifest["patches"]

    lines = [
        "# OpenCentauri Firmware Patch Summary",
        "",
        f"- Build version: `{build['version']}`",
        f"- Branch: `{build['branch']}`",
        f"- Commit: `{build['commit']}`",
        f"- Dirty tracked files: `{str(build['dirty']).lower()}`",
        f"- Original firmware: `{original['file_name']}`",
        f"- Original SHA-256: `{original['sha256']}`",
        f"- Final firmware: `{final['file_name']}`",
        f"- Final SHA-256: `{final['sha256']}`",
        "",
        "## Patches applied",
        "",
    ]

    if patches:
        lines.extend([
            "| Order | Patch | ID | Source |",
            "| ---: | --- | --- | --- |",
        ])
        for patch in patches:
            lines.append(
                f"| {patch['order']} | {patch['name']} | `{patch['id']}` | `{patch['path']}` |"
            )
    else:
        lines.append("No patches were applied.")

    with open(args.output, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
