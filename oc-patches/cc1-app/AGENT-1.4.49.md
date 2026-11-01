# CC1 App Binary Patch Map for Firmware 1.4.49

> **WARNING:** Any new patch must not overlap with existing code caves, branch hooks, or data strings. Overlapping patches will silently corrupt each other in the full patch chain. Always verify the full `patch_planner.py` build chain before committing a new patch.

## Executive Summary

The 1.4.49 app binary uses rodata zero runs as caves (the whole rodata sits in the **R-E LOAD segment**, so they hold code as well as data); the remaining patches are **in-place patches**. Claim zero-filled space in the table below before generating any patch that needs one.

| Cave Address | Used By | Size | End |
|--------------|---------|------|-----|
| `0x004517e0` | `spoof_slicer_firmware_version` (spoofed version string, `1.4.49 OC`) | 11 bytes | `0x004517ea` |
| `0x004517f0` | `wait_for_chamber_temp` trampoline (code) | 216 bytes | `0x004518c8` |
| `[0x4518d0,0x451994)` | `report_filament_usage` injected fn (code) | 196 bytes | `0x451993` |
| `0x004519a0` | `report_filament_usage` key strings (data) | 34 bytes | `0x004519c1` |

(All in the ~2KB rodata zero run `0x004517e0`–`0x00451fb8`. `report_filament_usage` also uses private BSS doubles at `0x00522f08`/`0x00522f10`; writable ELF allocation and exported end symbols extended to `0x00522f18` — runtime-zero, no file backing. Remaining free: `0x004519c2`–`0x00451fb8` (~1.5KB), the `0x00451fe3` run (~2KB), and four ~240B `0x0044exxx` slots. NOTE: the 1.4.46 cave `0x00450e00` is OCCUPIED in 1.4.49 — never reuse 1.4.46 cave addresses without checking. File→VA bias is `+0x10000` below file `0x48ed08` and `+0x20000` in the RW LOAD.)

## Patch-by-Patch Breakdown

### `set-firmware-version-patch` (1.4.49)
**Type:** Data string replacement (script-driven)
- File offset `0x003FAE10` (VA `0x0040ae10`): stock `"1.4.49\0\0"` replaced with the OpenCentauri version (e.g. `"0.5.1-oc"`).
- Applied by `patch.py` with a stock-bytes guard. Version string consumers (~15 sites, all `movw`/`movt` pairs) are left pointing at the same address.
- The version comes from `TOOLS/firmware_version.py`: `vX.Y.Z-integrate` branches report `X.Y.Z-beta-<sha>-oc`, otherwise the `OC_VERSION` value declared in `firmware-editions/patched` wins, otherwise `git describe --tags`. Bump `OC_VERSION` with each release.
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
- Disjoint from `set-firmware-version`; write order does not matter. Slicer sees `1.4.49 OC`, logs/UI/OTA keep the OC version.
- The `OC` marker is load-bearing: Home Assistant's `elegoo_printer` only creates the OpenCentauri-only filament sensors when `FirmwareVersion` carries an `OC`/`O` marker (`sensor.py` → `printer.open_centauri` → `Printer._is_open_centauri`). Without it, HA never registers `total_extrusion`/`current_extrusion` and Spoolman sees nothing, no matter what the printer pushes.
- The patch validates all four regions before writing any byte, and refuses if the cave is no longer zero (another patch claimed it).
**String cave at `0x004517e0`, 11 bytes.** See `spoof-slicer-firmware-version/README.md`.

### `allow-uploads-during-printing-patch` (1.4.49)
**Type:** Python direct binary patch (`patch.py` via `patch.sh` FW_VER branch; two-pass byte-guarded)
- NOPs the two busy-guard branches into the `device is busy,can't upload` error flow (`0x36b24c`) in the SDCP v3 HTTP handler `fcn.0036a5c8`:
  - `0x0036acb4` `beq` → `nop`; `0x0036acdc` `bne` → `nop`
**No cave used.** See `allow-uploads-during-printing-patch/README-1.4.49.md`.

### `allow-api-during-printing-patch` (1.4.49)
**Type:** Python direct binary patch (same runner pattern)
- NOPs the single busy-guard `bne 0x371e3c` at `0x00371bd0` in the set-status API `fcn.00371b10` (`device is busy,can't set status`).
**No cave used.** See `allow-api-during-printing-patch/README-1.4.49.md`.

### `do-not-block-z-offset-adjust-patch` (1.4.49)
**Type:** Python direct binary patch (same runner pattern)
- `app_z_offset_callback` `fcn.0034cb60`: BTN_DOWN `0x0034cc44` `bl 0x342a78` → `b 0x34cc5c`; BTN_UP `0x0034d20c` `bl 0x342a78` → `b 0x34d32c` (skips the print-state condition entirely; same relative deltas as 1.1.40).
**No cave used.** See `do-not-block-z-offset-adjust-patch/README-1.4.49.md`.

### `disable-exhaust-fan-patch` (1.4.49)
**Type:** Python direct binary patch (same runner pattern)
- NOPs both entries into the exhaust-fan control block of the periodic handler `0x35e388`: `0x0035e920` `bne 0x35e9e8` → `nop`; `0x0035e938` `bne 0x35ea08` → `nop`.
**No cave used.** See `disable-exhaust-fan-patch/README-1.4.49.md`.

### `wait-for-chamber-temp` (1.4.49)
**Type:** Hook + code cave trampoline (`patch.py` writes assembled blob from `trampoline-1.4.49.S`)
- Hook `0x00177d88` `bl 0xed8d8` → `b 0x4517f0`; trampoline in cave `0x004517f0` (216B).
- box path: `simple_bus_request` `0x2b874` for `srv_state` (`0x4440fc`), chamber double at state+0x48, wait loop `usleep(10000)` @ `0x1c544`, exit to epilogue `0x177f98`. MIN=d11 / MAX=d12 live at hook; SENSOR char* at handler `[sp+0x10]`.
- **Fix vs 1.4.46:** non-box sensors re-execute the clock `bl 0xed8d8` and resume at `0x177d8c` (stock heater TEMPERATURE_WAIT works; 1.4.46 sent them to the epilogue).
**Cave `0x004517f0`.** See `wait-for-chamber-temp/README-1.4.49.md`.

### `report-filament-usage` (1.4.49)
**Type:** Hook + code cave injected fn (`patch.py` writes assembled blob from `injected-1.4.49.S` + key strings)
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

See `report-filament-usage/README-1.4.49.md`.

## 1.4.49 Binary Notes

- Stock `app-1.4.49` sha256: `1a899b50fc104a38fe3f77cf4988c810da6670f3d0cc457de5d876c49fd76843` (from `FW/FW-CentauriCarbon-v1.4.49-2026-07-29.bin`). The `unpacked/squashfs-root/app/app` in a built tree is **already patched** — never use it as a patch baseline.
- Code/rodata VA = file offset + 0x10000; RW LOAD VA = file offset + 0x20000. BSS has no payload bytes in the file.
- String/code references are `movw`/`movt` pairs, but the compiler **interleaves the pair** (other instructions may sit between `movw` and its `movt`). When scanning for address references, allow a window of ~8 instructions between `movw rd, #lo` and `movt rd, #hi`.
- Gcode command strings live in a packed 8-byte-stride table in `.rodata` around `0x00416374`; handlers are registered by loading the handler address as an immediate next to the string load (see chamber-light README for the M8212/M8213 example).

## Collision Rules for New Patches

1. **Never reuse an existing cave.** Caves are zero-filled only in the stock binary; once a patch writes to it, the bytes are consumed.
2. **Never place a new cave inside another patch's cave boundary.**
3. **Always run `patch_planner.py 1.4.49 --dry-run` after adding a new patch.** It shows the full ordered patch chain. Then build with `sudo ./build.sh 1.4.49` and disassemble the final app to verify all cave addresses.
4. **Document new caves in this file.** If you add a patch that uses a code cave, append its address range to the table above and update the summary.
5. **Prefer in-place single-instruction patches when possible.** If the fix is just forcing a constant or removing a branch, patch the single instruction directly. This avoids cave contention entirely.
6. **Claim the next free cave from the top.** Existing cave claims are listed above. Verify the stock ELF mapping and full patch chain before allocating additional space; never reuse 1.4.46 addresses by assumption.
