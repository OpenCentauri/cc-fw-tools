#!/usr/bin/env python3
"""Remove stale printer.cfg and let the firmware app regenerate it.

Runs on boot from rc.local. If printer.cfg is absent, the firmware app creates
it automatically and this script leaves it alone. If an existing config is
stale, this script removes it and lets the app recreate it from the factory
config. The app also handles its normal user_printer.cfg overlay.
"""

import argparse
import hashlib
import os
import re


LIVE_CFG = "/board-resource/printer.cfg"
USER_CFG = "/board-resource/user_printer.cfg"
FACTORY_CFG = "/app/resources/configs/printer.cfg"
HOME_POSITION_ENDSTOP = "256.499"


def parse_config(path):
    """Parse a Klipper-style config into {section: {key: value, ...}}."""
    sections = {}
    current = None
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", ";")):
                continue
            match = re.match(r"^\[(.+?)\]", stripped)
            if match:
                current = match.group(1)
                sections.setdefault(current, {})
                continue
            if current is None:
                continue
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                sections[current][parts[0].strip()] = parts[1].strip()
    return sections


def factory_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        digest.update(file.read())
    return digest.hexdigest()[:16]


def marker_path(live_path):
    return f"{os.path.dirname(live_path) or '.'}/.oc_factory_hash"


def stored_factory_hash(live_path, user_path):
    """Read the new marker, with compatibility for older installs."""
    path = marker_path(live_path)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            return file.read().strip()

    # Older versions stored the marker in user_printer.cfg.
    if os.path.exists(user_path):
        for section in parse_config(user_path).values():
            if "_oc_factory_hash" in section:
                return section["_oc_factory_hash"]
    return None


def write_factory_hash(live_path, factory_path):
    path = marker_path(live_path)
    with open(path, "w", encoding="utf-8") as file:
        file.write(factory_hash(factory_path))
    print(f"Stored factory hash marker in {path}")


def needs_update(live_path, factory_path, user_path):
    """Return whether an existing live config should be removed."""
    with open(live_path, "r", encoding="utf-8") as file:
        live_text = file.read()

    # Old stock configs still reference the original MCU device.
    if "/dev/ttyACM0" in live_text:
        return True

    # The factory config shipped in the patched firmware contains this
    # signature. A live config without it is from before the patched factory.
    live_sections = parse_config(live_path)
    if live_sections.get("stepper_x", {}).get("position_endstop") != HOME_POSITION_ENDSTOP:
        return True

    # A changed factory config means the live config belongs to an older
    # firmware generation.
    return stored_factory_hash(live_path, user_path) != factory_hash(factory_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", default=LIVE_CFG)
    parser.add_argument("--user", default=USER_CFG)
    parser.add_argument("--factory", default=FACTORY_CFG)
    args = parser.parse_args()

    if not os.path.exists(args.factory):
        print("Factory printer.cfg not found, skipping.")
        return

    if not os.path.exists(args.live):
        # First boot: do not touch the absent config. Record the factory that
        # the app is about to use so its newly generated config is retained.
        write_factory_hash(args.live, args.factory)
        print("Live printer.cfg not found; leaving creation to the firmware app.")
        return

    if not needs_update(args.live, args.factory, args.user):
        print("Live printer.cfg already up to date, skipping.")
        return

    os.remove(args.live)
    print("Removed stale printer.cfg; the firmware app will regenerate it.")
    write_factory_hash(args.live, args.factory)


if __name__ == "__main__":
    main()
