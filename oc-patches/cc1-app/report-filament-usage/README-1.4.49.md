# Filament usage in CC1 1.4.49 SDCP status

Based on harpua555's original OpenCentauri/cc-fw-tools PR #40, shipped in v0.3.0.
This port emits `TotalExtrusion` and `CurrentExtrusion` beneath `Status.PrintInfo`.
Both lp55's PR #106 probe and the referenced Home Assistant parser accept these
plain names as well as the original ASCII-hex wire names.

`TotalExtrusion` reads `Printer -> PrintStats -> filament_used` at
`[[0x4b27bc]+0xf8]+0x1c0`. Stock PrintStats accumulates E movement divided by the
extrusion factor. `CurrentExtrusion` is the signed difference since the previous
status-writer invocation, not a speed or positive-only total. Stock print/reset
behavior is inherited; the patch adds no tray, client, or reset policy.
The historic 250-ms description is not a timer or timing guarantee in the cave.

## Mapping (virtual addresses unless explicitly labeled file offsets)

- Broadcast hook `0x36d310` / file `0x35d310`, replacing movt/vmov/vcvt.
- Pre-hook `movw r1,#0x96d0` remains stock; layer value is in r3.
- PrintInfo JSON object r8; native JSON-number helper `0x2c9b80` uses r0/r1/d0.
- Cave `[0x4518d0,0x451994)` is 196 bytes in the executable LOAD segment.
- Strings `0x4519a0` / `0x4519b0` hold the plain total/delta names.
- Private BSS doubles at `0x522f08` / `0x522f10`; allocated end `0x522f18`.
- Resume `0x36d320`, after the stock TotalLayer call; the cave emits it once.
- The former Agora hook `0x37f9ec` is left untouched.

Scratch is explicitly reserved by growing RW p_memsz (`0xc8`) from `0x741fc`
to `0x74210`, .bss sh_size (`0x492380`) from `0x710d4` to `0x710e8`, and the
four exported BSS/end symbol values at file offsets `0x1724`, `0x20a4`,
`0x3e34`, `0x4044` from `0x522f04` to `0x522f18`. File size/p_filesz do not grow.
The old port's `0x4b4788/0x4b4790` overlap stock PRNG state and are never used.

The patcher validates every guard/cave/key/allocation field before any write.
Wrong firmware, truncated files, cave collisions, and reapplication are rejected.
It runs only on disposable extracted rootfs files, not a running app.
The cave still has no ARM unwind entry; allocation exceptions inside it retain
the original accepted termination risk.

## Host checks (from repository root)

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --no-project --with unicorn==2.1.4 python3 tests/test_report_filament_usage.py -v
python3 TOOLS/check_filament_usage.py --self-test
python3 oc-patches/patch_planner.py 1.4.49 --dry-run
```

The binary regression uses pristine app-1.1.40 and app-1.4.49 from
`/home/paul/carbon/cc-firmware/stock/`; override ORIGINAL_STOCK_APP/STOCK_APP
when using another workspace. It executes the original and ported trampolines
with a mocked native JSON helper. This does not replace a device capture.

## Live check (only on an approved CC1 test device/build)

```bash
uv run --no-project --with websockets==13.1 python3 TOOLS/check_filament_usage.py "$PRINTER_IP" --seconds 30 --require-change
```

`--seconds` bounds connection opening and the observation window; closing does
not wait for a peer's close-handshake reply. WebSocket keepalive remains enabled.

Start a normal supervised print separately. Expected: finite numeric fields under
Status.PrintInfo, changing total and signed nonzero deltas during extrusion.
The observer sends no motion, heat, or print commands. Idle-only manual extrusion
may not update stock PrintStats, so it is not sufficient acceptance.
Source procedure: https://github.com/OpenCentauri/cc-fw-tools/pull/106#issuecomment-5357240641

## Home Assistant / Spoolman caveat

The independent slicer-version spoof may make HA identify this as stock firmware
and omit extrusion entities. Raw fields passing does not prove HA/Spoolman works.
Keep the spoof policy unchanged here; verify the installed integration's entity
registration and actual spool accounting before claiming end-to-end success.
