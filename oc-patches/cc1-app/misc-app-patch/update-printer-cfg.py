#!/usr/bin/env python3
"""Migrate user_printer.cfg calibration overrides into a fresh factory printer.cfg.

Runs on boot from rc.local. Only acts if the live printer.cfg is missing the
OpenCentauri homing patch or still references /dev/ttyACM0.

This mirrors the app's own behavior: at runtime the app loads printer.cfg,
overlays user_printer.cfg via Setuservalue(), and writes the merged result
back to printer.cfg. We do the same thing at boot when the factory config
has changed (firmware upgrade).

Additionally, we ensure the home position patch is always baked into the
resulting printer.cfg and user_printer.cfg.
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

# Home position patch values (from home-position-front-right-patch)
HOME_PATCH = {
    "stepper_x": {
        "position_endstop": "256.499",
    },
    "stepper_y": {
        "homing_force_retract": "30",
    },
}


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


def apply_home_patch(text):
    """Apply home position patch values to config text."""
    for section, keys in HOME_PATCH.items():
        sec_pattern = re.compile(
            rf"^(\[{re.escape(section)}\].*?)(?=\n\[|\Z)",
            re.MULTILINE | re.DOTALL,
        )

        def replace_keys(m):
            sec_text = m.group(0)
            for key, value in keys.items():
                key_pattern = re.compile(
                    rf"^(\s*{re.escape(key)}\s*:\s*)([^\n]*)",
                    re.MULTILINE,
                )
                if key_pattern.search(sec_text):
                    sec_text = key_pattern.sub(rf"\g<1>{value}", sec_text, count=1)
                else:
                    sec_text = sec_text.rstrip("\n") + f"\n{key} : {value}\n"
            return sec_text

        if sec_pattern.search(text):
            text = sec_pattern.sub(replace_keys, text, count=1)
        else:
            text = text.rstrip("\n") + f"\n\n[{section}]\n"
            for key, value in keys.items():
                text += f"{key} : {value}\n"
    return text


def build_new_config(user_path, factory_path):
    """Overlay user_printer.cfg sections onto factory config, return new text.

    This mirrors the app's Setuservalue() logic:
    - For each section in user_printer.cfg:
      - If section exists in factory: replace all matching keys with user values
      - If section doesn't exist in factory: append the whole section
    - Then apply the home position patch to ensure it's always present
    """
    with open(factory_path, "r", encoding="utf-8") as f:
        factory_text = f.read()

    # 1. Apply home position patch to factory base first
    factory_text = apply_home_patch(factory_text)

    # 2. If user_printer.cfg exists, overlay it
    if os.path.exists(user_path):
        user_sections = parse_config(user_path)
        user_blocks = extract_sections_text(user_path)

        for section, user_keys in user_sections.items():
            sec_pattern = re.compile(
                rf"^(\[{re.escape(section)}\].*?)(?=\n\[|\Z)",
                re.MULTILINE | re.DOTALL,
            )
            sec_match = sec_pattern.search(factory_text)

            if sec_match:
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
                            sec_text = sec_text.rstrip("\n") + f"\n{key} : {user_value}\n"
                    return sec_text

                factory_text = sec_pattern.sub(replace_keys_in_section, factory_text, count=1)
            else:
                factory_text = factory_text.rstrip("\n") + "\n\n"
                factory_text += user_blocks.get(section, f"[{section}]\n")

    # 3. Re-apply home position patch after user overlay
    # (ensures user values can't accidentally override the patch)
    factory_text = apply_home_patch(factory_text)

    return factory_text


def update_user_printer_cfg(user_path):
    """Update user_printer.cfg with home position patch values if it exists."""
    if not os.path.exists(user_path):
        return

    user_sections = parse_config(user_path)
    user_blocks = extract_sections_text(user_path)

    # Read current user_printer.cfg content
    with open(user_path, "r", encoding="utf-8") as f:
        user_text = f.read()

    # Apply home position patch
    user_text = apply_home_patch(user_text)

    with open(user_path, "w", encoding="utf-8") as f:
        f.write(user_text)
    print(f"Updated {user_path} with home position patch values.")


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

    # Build new printer.cfg with user_printer.cfg overlay + home patch
    new_text = build_new_config(user_path, factory_path)
    with open(live_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("Updated live printer.cfg with migrated settings and home position patch.")

    # Also update user_printer.cfg with home position patch
    update_user_printer_cfg(user_path)


if __name__ == "__main__":
    main()
