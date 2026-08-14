# Spoof Slicer Firmware Version (CC1 1.4.49)

## Purpose

Override the firmware version reported to ElegooSlicer in SDCP attribute responses
so the slicer sees the stock `1.4.49` version instead of the actual OpenCentauri
version (`0.5.0-beta-<sha>-oc`). The real version string at `0x0040ae10` is left
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
table) and receives the 7-byte string `1.4.49\0`, matching the stock 7-byte
copy before `sprintf("V%s", ...)`.

NOTE: the 1.4.46 cave `0x00450e00` is OCCUPIED in 1.4.49 (string data) — do not
reuse it.

## Relationship to `set-firmware-version`

Disjoint. `set-firmware-version` writes the REAL OpenCentauri version at
`0x0040ae10` (what the printer itself reports). This patch only repoints the
three SDCP readers to the cave; every other consumer of `0x40ae10` keeps
seeing the OC version. Write order between the two patches does not matter.

## Verification

- `patch.py` refuses to apply if the guard bytes differ (wrong firmware or
  already patched).
- After applying to a stock `app-1.4.49`: the three sites disassemble to
  `movw r3,#0x17e0; movt r3,#0x45`, `0x004517e0` reads `1.4.49\0`, and
  `0x0040ae10` is unchanged.
