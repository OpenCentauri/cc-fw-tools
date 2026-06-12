#!/usr/bin/env python3
"""Migrate user_printer.cfg calibration overrides into a fresh factory printer.cfg.

Runs on boot from rc.local. Only acts if the live printer.cfg is missing the
OpenCentauri homing patch or still references /dev/ttyACM0.

This mirrors the app's own behavior: at runtime the app loads printer.cfg,
overlays user_printer.cfg via Setuservalue(), and writes the merged result
back to printer.cfg. We do the same thing at boot when the factory config
has changed (firmware upgrade).
"""

import argparse
import os
import re
import shutil
from datetime import datetime

LIVE_CFG = "/board-resource/printer.cfg"
USER_CFG = "/board-resource/user_printer.cfg"
FACTORY_CFG = "/app/resources/configs/printer.cfg"
BACKUP_DIR = "/board-resource"


def parse_config(path):
    """Parse a Klipper-style config into {section: {key: value, ...}, ...}."""
    sections = {}
    current = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith(";"):
                continue
            m = re.match(r"^\[(.+?)\]", stripped)
            if m:
                current = m.group(1)
                sections.setdefault(current, {})
                continue
            if current is None:
                continue
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                sections[current][key] = value
    return sections


def extract_sections_text(path):
    """Extract all section text blocks from a config file."""
    blocks = {}
    current = None
    buffer = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            m = re.match(r"^\[(.+?)\]", stripped)
            if m:
                if current is not None and buffer:
                    blocks[current] = "".join(buffer)
                current = m.group(1)
                buffer = [line]
            elif current is not None:
                buffer.append(line)
        if current is not None and buffer:
            blocks[current] = "".join(buffer)
    return blocks


def needs_update(path):
    """Return True if the live config needs the migration."""
    if not os.path.exists(path):
        return False

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Trigger 1: still has old MCU serial reference -> ALWAYS replace
    if "/dev/ttyACM0" in text:
        return True

    # Trigger 2: missing OpenCentauri homing patch signature -> ALWAYS replace
    sections = parse_config(path)
    stepper_x = sections.get("stepper_x", {})
    if stepper_x.get("position_endstop") != "256.499":
        return True

    return False


def build_new_config(user_path, factory_path):
    """Overlay user_printer.cfg sections onto factory config, return new text.

    This mirrors the app's Setuservalue() logic:
    - For each section in user_printer.cfg:
      - If section exists in factory: replace all matching keys with user values
      - If section doesn't exist in factory: append the whole section
    """
    user_sections = parse_config(user_path)
    with open(factory_path, "r", encoding="utf-8") as f:
        factory_text = f.read()

    # Extract raw text blocks from user_printer.cfg for appending new sections
    user_blocks = extract_sections_text(user_path)

    for section, user_keys in user_sections.items():
        # Check if section exists in factory config
        sec_pattern = re.compile(
            rf"^(\[{re.escape(section)}\].*?)(?=\n\[|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        sec_match = sec_pattern.search(factory_text)

        if sec_match:
            # Section exists in factory -- overlay user keys
            def replace_keys_in_section(m):
                sec_text = m.group(0)
                for key, user_value in user_keys.items():
                    key_pattern = re.compile(
                        rf"^(\s*{re.escape(key)}\s*:\s*)([^\n]*)",
                        re.MULTILINE,
                    )
                    if key_pattern.search(sec_text):
                        sec_text = key_pattern.sub(
                            rf"\g<1>{user_value}", sec_text, count=1
                        )
                    else:
                        # Key missing in factory section -- append it
                        sec_text = sec_text.rstrip("\n") + f"\n{key} : {user_value}\n"
                return sec_text

            factory_text = sec_pattern.sub(replace_keys_in_section, factory_text, count=1)
        else:
            # Section doesn't exist in factory -- append whole section from user
            factory_text = factory_text.rstrip("\n") + "\n\n"
            factory_text += user_blocks.get(section, f"[{section}]\n")

    return factory_text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", default=LIVE_CFG)
    parser.add_argument("--user", default=USER_CFG)
    parser.add_argument("--factory", default=FACTORY_CFG)
    args = parser.parse_args()

    live_path = args.live
    user_path = args.user
    factory_path = args.factory

    if not os.path.exists(live_path):
        print("Live printer.cfg not found, skipping.")
        return
    if not os.path.exists(factory_path):
        print("Factory printer.cfg not found, skipping.")
        return
    if not needs_update(live_path):
        print("Live printer.cfg already up to date, skipping.")
        return

    # Backup
    today = datetime.now().strftime("%Y%m%d")
    backup_dir = os.path.dirname(live_path) or "."
    backup_name = f"{backup_dir}/printer.cfg-backup{today}"
    suffix = ""
    counter = 1
    while os.path.exists(backup_name + suffix):
        suffix = f"-{counter}"
        counter += 1
    backup_path = backup_name + suffix
    shutil.copy2(live_path, backup_path)
    print(f"Backed up live printer.cfg to {backup_path}")

    # If user_printer.cfg exists, overlay it onto factory config.
    # If it doesn't exist, just use the factory config as-is (fresh install
    # or user never calibrated).
    if os.path.exists(user_path):
        new_text = build_new_config(user_path, factory_path)
    else:
        with open(factory_path, "r", encoding="utf-8") as f:
            new_text = f.read()

    with open(live_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("Updated live printer.cfg with migrated settings.")


if __name__ == "__main__":
    main()
