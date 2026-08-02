# CC1 App Binary Patch Map for Firmware 1.4.49

> **WARNING:** Any new patch must not overlap with existing code caves, branch hooks, or data strings. Overlapping patches will silently corrupt each other in the full patch chain. Always verify the full `patch_planner.py` build chain before committing a new patch.

## Executive Summary

The 1.4.49 app binary uses one **string cave** (data only, no code injection); all other patches are **in-place patches** (existing function bodies rewritten, single instructions, or data strings). Claim zero-filled space in the table below before generating any patch that needs one.

| Cave Address | Used By | Size | End |
|--------------|---------|------|-----|
| `0x004517e0` | `spoof_slicer_firmware_version` (spoofed `"1.4.49\0"` string) | 8 bytes | `0x004517e7` |

(0x004517e0 sits in a ~2KB zero run in `.rodata` ending `0x00451fb8`; the remainder is unclaimed. NOTE: the 1.4.46 cave `0x00450e00` is OCCUPIED in 1.4.49 — never reuse 1.4.46 cave addresses without checking.)

## Patch-by-Patch Breakdown

### `set-firmware-version-patch` (1.4.49)
**Type:** Data string replacement (script-driven)
- File offset `0x003FAE10` (VA `0x0040ae10`): stock `"1.4.49\0\0"` replaced with the OpenCentauri git-describe version (e.g. `"0.5.0-<sha>-oc"`).
- Applied by `patch.py` with a stock-bytes guard. Version string consumers (~15 sites, all `movw`/`movt` pairs) are left pointing at the same address.
**No cave used.**

### `add-chamber-light-gcode-patch` (1.4.49)
**Type:** Existing function body rewrite
- `0x000a5d98` — `M8212` handler rewritten in-place (camera + mainboard light OFF)
- `0x000a5e50` — `M8213` handler rewritten in-place (camera + mainboard light ON)
- Calls `camera_light_control` `0x002f53d8`, `mainboard_light_control` `0x001971cc`; light object via singleton global `0x004b27bc`, member offset `0x218`.
- Byte guard: `verify-1.4.49.py` checks the exact spans the bsdiff writes (before/after `bspatch`); regenerate both with `generate_patch.py` if the bodies are re-assembled.
**No cave used.** See `add-chamber-light-gcode-patch/README-1.4.49.md`.

### `ota-updates-patch` (1.4.49)
**Type:** Function redirects + data string replacement
- `0x002f9490` — `hl_net_wan_is_connected` → branch to `hl_net_lan_is_connected` `0x002f944c`
- `0x002fa658` — `hl_netif_wan_is_connected` → branch to `hl_netif_lan_is_connected` `0x002fa620`
- `0x002c32cc` — `is_ota_version_greater` → check system OTA version is empty string
- `0x004487a4` — string `"https://mms.chituiot.com/"` → `"https://u.opencentauri.cc/"`
**No cave used.** See `ota-updates-patch/README-1.4.49.md`.

### `home-position-front-right-patch` (1.4.49)
**Type:** Config patch (`.diff` on `printer.cfg`)
**No binary cave used.**

### `misc-app-patch` (1.4.49)
**Type:** Rootfs/config patch (rc.local, boot logo, `update-printer-cfg.py`)
**No binary cave used.**

### `spoof-slicer-firmware-version` (1.4.49)
**Type:** Python direct binary patch (`patch.py`, byte-guarded; refuses on mismatch)
- Repoints the version-string source in the three SDCP `FirmwareVersion` paths from `0x0040ae10` to the string cave `0x004517e0`:
  - UDP discovery responder: site `0x00369974` (file `0x00359974`)
  - WebSocket/MQTT attributes: site `0x0036bd64` (file `0x0035bd64`)
  - Direct request-attribute: site `0x0037fbe4` (file `0x0036fbe4`)
- Guard bytes (all three sites): `103e0ae3 403040e3` → new bytes `e03701e3 453040e3` (`movw r3,#0x17e0; movt r3,#0x45`).
- Disjoint from `set-firmware-version`; write order does not matter. Slicer sees `1.4.49`, logs/UI/OTA keep the OC version.
**String cave at `0x004517e0`.** See `spoof-slicer-firmware-version/README.md`.

## 1.4.49 Binary Notes

- Stock `app-1.4.49` sha256: `1a899b50fc104a38fe3f77cf4988c810da6670f3d0cc457de5d876c49fd76843` (from `FW/FW-CentauriCarbon-v1.4.49-2026-07-29.bin`). The `unpacked/squashfs-root/app/app` in a built tree is **already patched** — never use it as a patch baseline.
- Uniform file→VA bias: `VA = file_offset + 0x10000` for all sections.
- String/code references are `movw`/`movt` pairs, but the compiler **interleaves the pair** (other instructions may sit between `movw` and its `movt`). When scanning for address references, allow a window of ~8 instructions between `movw rd, #lo` and `movt rd, #hi`.
- Gcode command strings live in a packed 8-byte-stride table in `.rodata` around `0x00416374`; handlers are registered by loading the handler address as an immediate next to the string load (see chamber-light README for the M8212/M8213 example).

## Collision Rules for New Patches

1. **Never reuse an existing cave.** Caves are zero-filled only in the stock binary; once a patch writes to it, the bytes are consumed.
2. **Never place a new cave inside another patch's cave boundary.**
3. **Always run `patch_planner.py 1.4.49 --dry-run` after adding a new patch.** It shows the full ordered patch chain. Then build with `sudo ./build.sh 1.4.49` and disassemble the final app to verify all cave addresses.
4. **Document new caves in this file.** If you add a patch that uses a code cave, append its address range to the table above and update the summary.
5. **Prefer in-place single-instruction patches when possible.** If the fix is just forcing a constant or removing a branch, patch the single instruction directly. This avoids cave contention entirely.
6. **Claim the next free cave from the top.** No caves are claimed yet for 1.4.49. The 1.4.46 cave region lived at `0x00450100`+; re-discover zero-filled executable space in the 1.4.49 binary before claiming anything, and document exact start/end here and in the patch README.
