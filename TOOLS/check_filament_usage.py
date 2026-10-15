#!/usr/bin/env python3
"""Read-only, bounded adaptation of lp55's cc-fw-tools PR #106 observer.

Source: https://github.com/OpenCentauri/cc-fw-tools/pull/106#issuecomment-5357240641
This script does not heat, move, extrude, upload files, or start a print.
"""
import argparse
import asyncio
import json
import math
import sys
import time

FIELDS = (
    ("TotalExtrusion", "54 6F 74 61 6C 45 78 74 72 75 73 69 6F 6E 00"),
    ("CurrentExtrusion", "43 75 72 72 65 6E 74 45 78 74 72 75 73 69 6F 6E 00"),
)


def extract_usage(message):
    if not isinstance(message, dict):
        return None
    status = message.get("Status")
    if not isinstance(status, dict) or not isinstance(status.get("PrintInfo"), dict):
        return None
    info = status["PrintInfo"]
    result = {}
    for plain, legacy in FIELDS:
        key = plain if plain in info else legacy
        value = info.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return None
        result[key] = value
    return result


def self_test():
    normal = {"Status": {"PrintInfo": {"TotalExtrusion": 0.0, "CurrentExtrusion": -2.0}}}
    assert extract_usage(normal) == normal["Status"]["PrintInfo"]
    legacy = {"Status": {"PrintInfo": {FIELDS[0][1]: 10.0, FIELDS[1][1]: 3.0}}}
    assert extract_usage(legacy) == legacy["Status"]["PrintInfo"]
    mixed = {"Status": {"PrintInfo": {"TotalExtrusion": 0.0, FIELDS[0][1]: 99.0, FIELDS[1][1]: 0.0}}}
    assert extract_usage(mixed) == {"TotalExtrusion": 0.0, FIELDS[1][1]: 0.0}
    for value in (None, True, "1", float("nan"), float("inf")):
        assert extract_usage({"Status": {"PrintInfo": {"TotalExtrusion": value, "CurrentExtrusion": 0.0}}}) is None
    assert extract_usage({"Status": {"PrintInfo": {}}}) is None
    assert extract_usage({"Data": {"TotalExtrusion": 10, "CurrentExtrusion": 3}}) is None
    print("filament observer parser self-test passed")


async def observe(ip, seconds, require_change):
    import websockets
    good = 0
    changed = False
    deadline = time.monotonic() + seconds
    # ponytail: no extra close-handshake wait after the observation deadline.
    async with websockets.connect(f"ws://{ip}:3030/websocket", open_timeout=seconds, close_timeout=0) as ws:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                break
            try:
                message = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                continue
            usage = extract_usage(message)
            if usage is not None:
                good += 1
                delta_key = FIELDS[1][0] if FIELDS[1][0] in usage else FIELDS[1][1]
                changed |= usage[delta_key] != 0
                print(json.dumps({"at": time.monotonic(), "Status": {"PrintInfo": usage}}), flush=True)
    print(f"numeric_samples={good} nonzero_delta={changed}", file=sys.stderr)
    return 0 if good and (changed or not require_change) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ip", nargs="?")
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--require-change", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.ip or not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error("provide a printer IP and a positive finite --seconds")
    try:
        return asyncio.run(observe(args.ip, args.seconds, args.require_change))
    except Exception as exc:
        print(f"filament observer failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
