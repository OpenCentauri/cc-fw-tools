#!/usr/bin/env python3
"""Migrate calibration settings from live printer.cfg into factory printer.cfg.

Runs on boot from rc.local. Only acts if the live config is missing the
OpenCentauri homing patch or still references /dev/ttyACM0.
"""

import argparse
import os
import re
import shutil
from datetime import datetime

LIVE_CFG = "/board-resource/printer.cfg"
FACTORY_CFG = "/app/resources/configs/printer.cfg"
BACKUP_DIR = "/board-resource"

# Sections and the specific keys we want to migrate from live -> factory
MIGRATE_SECTIONS = {
    "input_shaper": ["shaper_freq_x", "shaper_type_y", "shaper_freq_y"],
    "stepper_x": ["homing_retract_dist", "homing_force_retract", "position_endstop"],
    "stepper_y": ["homing_retract_dist", "homing_force_retract", "position_endstop"],
    "stepper_z": ["position_endstop"],
    "extruder": ["pid_Kp", "pid_Ki", "pid_Kd"],
    "heater_bed": ["pid_Kp", "pid_Ki", "pid_Kd"],
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
            # key : value  (colon-separated, optional whitespace)
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                sections[current][key] = value
    return sections


def extract_sections_text(path, section_names):
    """Extract raw text blocks for given section names (exact match)."""
    blocks = {}
    current = None
    buffer = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            m = re.match(r"^\[(.+?)\]", stripped)
            if m:
                if current in section_names and buffer:
                    blocks[current] = "".join(buffer)
                current = m.group(1)
                buffer = [line]
            elif current is not None:
                buffer.append(line)
        if current in section_names and buffer:
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


def build_new_config(live_path, factory_path):
    """Layer live values over factory config, return new text."""
    live_sections = parse_config(live_path)
    with open(factory_path, "r", encoding="utf-8") as f:
        factory_text = f.read()

    # 1. Migrate specific keys in known sections
    # Only overlay live values that differ from factory (preserves calibration
    # changes while keeping factory defaults/OpenCentauri patches for
    # uncalibrated keys).
    # If the live config is missing the homing patch, it has stock values for
    # these keys -- skip migration and use factory defaults.
    factory_sections = parse_config(factory_path)
    live_has_homing_patch = live_sections.get("stepper_x", {}).get("position_endstop") == "256.499"
    for section, keys in MIGRATE_SECTIONS.items():
        live_vals = live_sections.get(section, {})
        factory_vals = factory_sections.get(section, {})
        for key in keys:
            if key in live_vals:
                # If live config is missing homing patch, skip migration for
                # these keys (live has stock values, not calibration values)
                if not live_has_homing_patch:
                    continue
                # Only migrate if live value differs from factory
                if live_vals[key] == factory_vals.get(key):
                    continue
                # Scoped replacement: only within the target section
                sec_pattern = re.compile(
                    rf"^(\[{re.escape(section)}\].*?)(?=\n\[|\Z)",
                    re.MULTILINE | re.DOTALL,
                )
                def replace_key_in_section(m):
                    sec_text = m.group(0)
                    key_pattern = re.compile(
                        rf"^(\s*{re.escape(key)}\s*:\s*)([^\n]*)",
                        re.MULTILINE,
                    )
                    if key_pattern.search(sec_text):
                        return key_pattern.sub(rf"\g<1>{live_vals[key]}", sec_text, count=1)
                    else:
                        # Key missing in section -- append it
                        return sec_text.rstrip("\n") + f"\n{key} : {live_vals[key]}\n"

                if sec_pattern.search(factory_text):
                    factory_text = sec_pattern.sub(replace_key_in_section, factory_text, count=1)
                else:
                    # Section missing entirely -- append at end
                    factory_text = factory_text.rstrip("\n") + f"\n\n[{section}]\n{key} : {live_vals[key]}\n"

    # 2. Copy any [besh_profile_*] sections from live config in whole
    besh_names = [s for s in live_sections if s.startswith("besh_profile_")]
    if besh_names:
        besh_blocks = extract_sections_text(live_path, set(besh_names))
        # Append live besh_profile sections at the end (keep factory ones if present)
        factory_text = factory_text.rstrip("\n") + "\n\n"
        for name in sorted(besh_names):
            factory_text += besh_blocks.get(name, "")

    return factory_text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", default=LIVE_CFG)
    parser.add_argument("--factory", default=FACTORY_CFG)
    args = parser.parse_args()

    live_path = args.live
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
    # Avoid overwriting an existing backup for the same day
    suffix = ""
    counter = 1
    while os.path.exists(backup_name + suffix):
        suffix = f"-{counter}"
        counter += 1
    backup_path = backup_name + suffix
    shutil.copy2(live_path, backup_path)
    print(f"Backed up live printer.cfg to {backup_path}")

    new_text = build_new_config(live_path, factory_path)
    with open(live_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("Updated live printer.cfg with migrated settings.")


if __name__ == "__main__":
    main()
