# Spoof Slicer Firmware Version (CC1 1.4.49)

## Purpose

Override the firmware version reported to ElegooSlicer in SDCP attribute responses
so the slicer sees a stock-shaped `1.4.49 OC` instead of the actual OpenCentauri
version (`0.5.1-oc`). The real version string at `0x0040ae10` is left
untouched so local logs, UI labels, and OTA update checks still show the correct
version.

Port of the 1.4.46 patch (`spoof-slicer-firmware-version`).

## Affected SDCP paths

All three paths that emit a `FirmwareVersion` field are patched. Each loads the
version string `0x0040ae10` with an identical instruction pair
(`103e0ae3 403040e3` = `movw r3,#0xae10; movt r3,#0x40`), which is the byte guard:

| Path | Site VA | File offset |
|----------|-----|-----|
| UDP discovery responder | `0x00369974` | `0x00359974` |
| WebSocket/MQTT attributes topic | `0x0036bd64` | `0x0035bd64` |
| Direct request-attribute response | `0x0037fbe4` | `0x0036fbe4` |

UDP site identity confirmed via neighboring strings `"sdcp :: udp init"` and
`"M99999"`. These are the only refs to `0x40ae10` in the `0x36xxxx-0x37xxxx`
SDCP region; the `0x34xxxx-0x35xxxx` cluster is UI/display and `0x1d4c4` is the
`main()` startup log — all untouched.

## Mechanism

Each site is repointed to a code-cave string at `0x004517e0`:

```arm
movw r3, #0x17e0
movt r3, #0x45     ; r3 = 0x004517e0
```

The cave is a 2KB zero run in `.rodata` (claimed in `../AGENT-1.4.49.md` cave
table) and receives the 11-byte string `1.4.49 OC\0`, ending at `0x004517ea` -
the next claim (`wait_for_chamber_temp`) starts at `0x004517f0`. The stock copy
before `sprintf("V%s", ...)` was 7 bytes; the output buffer is 0x80+, so the
extra bytes cost nothing at runtime.

## Why the `OC` marker

ElegooSlicer needs a version it recognises, but Home Assistant's `elegoo_printer`
integration needs to know the firmware is OpenCentauri. It only registers the
OpenCentauri-only sensors - `total_extrusion` / `current_extrusion`, which Spoolman
reads - when `Printer._is_open_centauri(model, firmware)` finds an `OC`/`O` marker in
the reported `FirmwareVersion` (`sensor.py` → `printer.open_centauri` →
`PRINTER_STATUS_FDM_OPEN_CENTAURI`). A bare `1.4.49` makes HA treat the printer as
stock and the extrusion entities are never created at all.

So the spoofed string is `1.4.49 OC` → clients see `V1.4.49 OC`: the leading version
keeps the slicer happy, the marker keeps HA on the OpenCentauri entity set.
`tests/test_spoof_slicer_firmware_version.py` locks both halves of that contract.

NOTE: the 1.4.46 cave `0x00450e00` is OCCUPIED in 1.4.49 (string data) — do not
reuse it.

## Relationship to `set-firmware-version`

Disjoint. `set-firmware-version` writes the REAL OpenCentauri version at
`0x0040ae10` (what the printer itself reports). This patch only repoints the
three SDCP readers to the cave; every other consumer of `0x40ae10` keeps
seeing the OC version. Write order between the two patches does not matter.

## Verification

- `patch.py` validates all four regions before writing a byte, and refuses if the
  guard bytes differ (wrong firmware or already patched) or the cave is no longer
  zero-filled (another patch claimed it).
- After applying to a stock `app-1.4.49`: the three sites disassemble to
  `movw r3,#0x17e0; movt r3,#0x45`, `0x004517e0` reads `1.4.49 OC\0`, and
  `0x0040ae10` is unchanged.
- `tests/test_spoof_slicer_firmware_version.py` covers the byte patch, the cave
  string, region confinement, non-mutating guard failures, and the HA/slicer
  contract on the reported string.
