#!/usr/bin/env python3
"""Create a build-details manifest for a firmware update."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from firmware_version import firmware_version


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(repo_root: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", repo_root, *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def git_metadata(repo_root: str) -> dict:
    try:
        branch = os.getenv("OC_BUILD_BRANCH")
        if not branch:
            try:
                branch = git_output(repo_root, "symbolic-ref", "--quiet", "--short", "HEAD")
            except subprocess.CalledProcessError:
                branch = "detached"

        commit = os.getenv("OC_BUILD_COMMIT") or git_output(repo_root, "rev-parse", "HEAD")
        short_commit = git_output(repo_root, "rev-parse", "--short=12", commit)

        # Restrict the diff pathspec to files present in HEAD. This detects
        # staged and unstaged changes to tracked files while ignoring all
        # untracked files, including staged additions.
        tracked_files = git_output(repo_root, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
        dirty = subprocess.run(
            ["git", "-C", repo_root, "diff", "--quiet", "HEAD", "--", *tracked_files],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        ).returncode != 0
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or "git metadata is unavailable"
        raise SystemExit(f"Error reading git metadata: {detail}") from error

    # Keep the version suitable for filenames and package metadata while
    # preserving the original branch name in the separate branch field.
    version_branch = re.sub(r"[^A-Za-z0-9._-]+", "-", branch).strip(".-") or "detached"
    version = f"oc-{version_branch}-g{short_commit}"
    if dirty:
        version += "-dirty"

    metadata = {
        "version": version,
        "branch": branch,
        "commit": commit,
        "dirty": dirty,
    }
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, help="Original firmware file passed to unpack.sh")
    parser.add_argument("--patch-list", required=True, help="JSON list written by patch_planner.py")
    parser.add_argument("--final", required=True, help="Final packed firmware file")
    parser.add_argument("--output", required=True, help="Manifest JSON output path")
    parser.add_argument("--repo-root", required=True, help="Git repository containing the build")
    args = parser.parse_args()

    for path in (args.original, args.patch_list, args.final):
        if not os.path.isfile(path):
            raise SystemExit(f"Error: required manifest input not found: {path}")

    with open(args.patch_list) as file:
        patches = json.load(file)

    build = git_metadata(args.repo_root)
    if any(patch["id"] == "set_firmware_version" for patch in patches):
        try:
            build["firmware_version"] = firmware_version(args.repo_root)
        except subprocess.CalledProcessError:
            build["firmware_version"] = "Unknown-oc"

    manifest = {
        "manifest_version": 1,
        "original_firmware": {
            "file_name": os.path.basename(args.original),
            "sha256": sha256(args.original),
        },
        "patches": patches,
        "final_firmware": {
            "file_name": os.path.basename(args.final),
            "path": args.final,
            "sha256": sha256(args.final),
        },
        "build": build,
    }

    with open(args.output, "w") as file:
        json.dump(manifest, file, indent=2)
        file.write("\n")


if __name__ == "__main__":
    main()
