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


def _declared_version(repo_root: str) -> str | None:
    """OC_VERSION from the build env, else from the active patch_config edition.

    patch_planner injects the edition variables into the environment of the patch
    scripts it launches, but the manifest and patch-summary tools run as separate
    processes to that planner. Reading the edition file here keeps the reported
    version identical to the one written into app/app.
    """
    value = os.getenv("OC_VERSION")
    if value:
        return value
    edition = os.path.join(repo_root, "oc-patches", "patch_config")
    try:
        with open(edition, encoding="utf-8") as stream:
            for line in stream:
                line = line.split("#", 1)[0].strip()
                key, separator, val = line.partition("=")
                if separator and key.strip() == "OC_VERSION" and val.strip():
                    return val.strip().strip("'\"")
    except OSError:
        return None
    return None


def firmware_version(repo_root: str) -> str:
    """Return the OpenCentauri firmware version for the build commit."""
    # Integration branches named vX.Y.Z-integrate are pre-release dev lines:
    # report X.Y.Z-beta-<sha> instead of the last release tag. OC_BUILD_BRANCH
    # is passed through the sudo env chain by build.sh; GITHUB_REF_NAME covers
    # unsudoed CI steps; fall back to the local branch name.
    branch = (
        os.getenv("OC_BUILD_BRANCH")
        or os.getenv("GITHUB_REF_NAME")
        or _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    )
    m = re.fullmatch(r"v?(\d+\.\d+\.\d+)-integrate", branch)
    if m:
        sha = os.getenv("OC_BUILD_COMMIT") or _git(
            repo_root, "rev-parse", "--short", "HEAD"
        )
        return f"{m.group(1)}-beta-{sha[:7]}-oc"

    # Release builds declare the version they ship instead of inheriting whatever
    # tag git-describe lands on: main is always ahead of the last release tag, so
    # describe would report the previous version plus a commit count.
    declared = _declared_version(repo_root)
    if declared:
        m = re.fullmatch(r"v?(\d+\.\d+\.\d+)", declared.strip())
        if not m:
            raise ValueError(f"OC_VERSION must be X.Y.Z or vX.Y.Z, got {declared!r}")
        return f"{m.group(1)}-oc"

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
