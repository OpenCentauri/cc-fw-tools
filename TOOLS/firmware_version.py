#!/usr/bin/env python3
"""Derive the version string written into app/app by the firmware version patch."""

import os
import subprocess


def firmware_version(repo_root: str) -> str:
    """Return the OpenCentauri firmware version for the build commit."""
    command = ["git", "-C", repo_root, "describe", "--tags"]
    build_commit = os.getenv("OC_BUILD_COMMIT")
    if build_commit:
        command.append(build_commit)

    described = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    parts = described.split("-")

    if len(parts) >= 3:
        version = f"{parts[0]}-{parts[2][1:]}"
    else:
        version = parts[0]

    if version.startswith("v"):
        version = version[1:]

    return f"{version}-oc"
