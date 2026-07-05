# Spoof Slicer Firmware Version (CC1 1.4.46)

## Purpose

Override the firmware version reported to ElegooSlicer in SDCP attribute responses
so the slicer sees the stock `1.4.46` version instead of the actual OpenCentauri
git-describe version. The real version string at `0x00409a38` is left untouched
so local logs, UI labels, and OTA update checks still show the correct version.

## Affected SDCP paths

All three paths that emit a `FirmwareVersion` field are patched:

| Function | VA | Use |
|----------|-----|-----|
| UDP discovery responder | `0x0036859c` | Broadcast response on LAN |
| WebSocket/MQTT attributes topic | `0x0036a98c` | `sub_36a948` |
| Direct request-attribute response | `0x0037e80c` | `sub_37e730` |

## Mechanism

Each function originally loads the source version string via:

```arm
movw r3, #0x9a38
movt r3, #0x40     ; r3 = 0x00409a38
```

The patch repoints all three to a new code-cave string at `0x00450e00`:

```arm
movw r3, #0x0e00
movt r3, #0x45     ; r3 = 0x00450e00
```

The cave contains the 7-byte string `1.4.46\0`, which fits the existing 7-byte
copy (`ldm r3, {r0, r1}` plus one byte) before `sprintf("V%s", ...)`.

## Cave

- `0x00450e00` — `0x00450e06` (7 bytes)

## Verification

After applying `spoof-slicer-firmware-version-1.4.46.bsdiff`:

```bash
arm-none-eabi-objdump -b binary -m arm -D \
  -M reg-names-std --adjust-vma=0x10000 app-1.4.46 \
  --start-address=0x36859c --stop-address=0x3685a4
arm-none-eabi-objdump ... --start-address=0x36a98c --stop-address=0x36a994
arm-none-eabi-objdump ... --start-address=0x37e80c --stop-address=0x37e814
```

All three should show `movw r3, #0x0e00` / `movt r3, #0x45`.
