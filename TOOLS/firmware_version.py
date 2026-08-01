#!/usr/bin/env python3
"""Derive the version string written into app/app by the firmware version patch."""

import os
import re
import subprocess


def _git(repo_root: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", repo_root, *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def firmware_version(repo_root: str) -> str:
    """Return the OpenCentauri firmware version for the build commit."""
    # Integration branches named vX.Y.Z-integrate are pre-release dev lines:
    # report X.Y.Z-beta-<sha> instead of the last release tag. GITHUB_REF_NAME
    # covers CI (detached HEAD); fall back to the local branch name.
    branch = os.getenv("GITHUB_REF_NAME") or _git(
        repo_root, "rev-parse", "--abbrev-ref", "HEAD"
    )
    m = re.fullmatch(r"v?(\d+\.\d+\.\d+)-integrate", branch)
    if m:
        sha = os.getenv("OC_BUILD_COMMIT") or _git(
            repo_root, "rev-parse", "--short", "HEAD"
        )
        return f"{m.group(1)}-beta-{sha[:7]}-oc"

    command = ["describe", "--tags"]
    build_commit = os.getenv("OC_BUILD_COMMIT")
    if build_commit:
        command.append(build_commit)
    described = _git(repo_root, *command)
    parts = described.split("-")

    if len(parts) >= 3:
        version = f"{parts[0]}-{parts[2][1:]}"
    else:
        version = parts[0]

    if version.startswith("v"):
        version = version[1:]

    return f"{version}-oc"
