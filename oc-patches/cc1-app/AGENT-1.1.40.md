# CC1 App Binary Patch Map for Firmware 1.1.40

> **WARNING:** Any new patch must not overlap with existing code caves, branch hooks, or data strings. Overlapping patches will silently corrupt each other in the full patch chain. Always verify the full `patch_planner.py` build chain before committing a new patch.

## Executive Summary

The 1.1.40 app binary uses two **injected code caves** (new trampolines written into zero-filled executable space) and several **in-place patches** (single instructions or existing function bodies modified directly). The two caves are:

| Cave Address | Used By | Size | End |
|--------------|---------|------|-----|
| `0x00391EC0` | `wait-for-chamber-temp` | 0xd4 bytes | `0x00391F94` |
| `0x00392680` | `report-filament-usage` | 0xc8 bytes | `0x00392747` |

There are **no other code caves** in the current 1.1.40 patch set. The next available zero-filled region after `0x00392747` is unallocated; any new patch needing a cave should claim from there and document it here.

## Patch-by-Patch Breakdown

### `wait-for-chamber-temp` (1.1.40)
**Type:** Branch-hook trampoline cave
**Cave:** `0x00391EC0` — `0x00391F94` (0xd4 bytes)
**Branch hook:**
- `0x00165A30` → `0x00391EC0` (was `bl sub_e2408`)
**Original bytes:** `0x00165A30: EB FD F2 74 → 22 B1 08 EA`

### `report-filament-usage` (1.1.40)
**Type:** Branch-hook trampoline cave + data strings
**Cave:** `0x00392680` — `0x00392747` (0xc8 bytes)
**Branch hook:**
- `0x002DEB18` → `0x00392680` (replaced `movt/vmov/vcvt` sequence; also clobbers `0x002DEB20`)
**Data strings:**
- `0x003925A0` — total key string
- `0x00392630` — current delta key string

### `add-chamber-light-gcode-patch` (1.1.40)
**Type:** Existing function body rewrite
- `cmd_m8212` handler rewritten in-place
- `cmd_m8213` handler rewritten in-place
**Branch targets (corrected offsets):**
- `bl 0x1f1d4c` → `camera_light_control`
- `bl 0xe6474` → `mainboard_light_control` (M8212)
- `bl 0x1f1c94` → `camera_light_control`
- `bl 0xe63bc` → `mainboard_light_control` (M8213)
**No cave used.**

### `ota-updates-patch` (1.1.40)
**Type:** Function redirects + data string replacement
- `sub_29475c` (`hl_net_wan_is_connected`) → redirect to `sub_294718` (`hl_net_lan_is_connected`)
- `sub_295924` (`hl_netif_wan_is_connected`) → redirect to `sub_2958ec` (`hl_netif_lan_is_connected`)
- `sub_261e6c` (`is_ota_version_greater`) → check `ota_ctx.info[OTA_FIREMARE_CH_SYS].version` is empty string
- String `"https://mms.chituiot.com/"` → `"https://u.opencentauri.cc/"`
**No cave used.**

### `allow-api-during-printing-patch` (1.1.40)
**Type:** In-place binary patch
- `0x002e2638` — patch out `if (r0_14 == 1 || r0_16)` that contains the string `"device is busy,can't set status
"`
**No cave used.**

### `allow-uploads-during-printing-patch` (1.1.40)
**Type:** In-place binary patch
- `sub_002dbdb0` — patch out the error flow with the string `"device is busy,can't upload"`
**No cave used.**

### `block-connectivity-check-patch` (1.1.40)
**Type:** In-place binary patch
- Patch past `hl_tpool_create_thread` and `hl_tpool_wait_started` calls in WAN connect detection routine
**No cave used.**

### `disable-exhaust-fan-patch` (1.1.40)
**Type:** In-place binary patch
- `0x002d6654` — patch out `if (result)` at the bottom of the function containing `"real_fan_speed = %d"`
**No cave used.**

### `do-not-block-z-offset-adjust-patch` (1.1.40)
**Type:** In-place binary patch
- Patch out the `if (app_print_get_print_state() && (!app_print_get_print_busy() || !app_top_get_autoleveling_busy()))` check using `b` jumps
**No cave used.**

### `set-firmware-version-patch` (1.1.40 only)
**Type:** Script-driven patch
- Runs `./patch.py` to inject version string at a known binary offset
**No cave used.**

### `home-position-front-right-patch` (1.1.40)
**Type:** Config patch (`.diff` on `printer.cfg`)
**No binary cave used.**

## Collision Rules for New Patches

1. **Never reuse an existing cave.** Caves are zero-filled only in the stock binary; once a patch writes to it, the bytes are consumed.
2. **Never place a new cave inside another patch's cave boundary.**
3. **Always run `patch_planner.py 1.1.40 --dry-run` after adding a new patch.** It shows the full ordered patch chain. Then build with `sudo ./build.sh 1.1.40` and disassemble the final app to verify all cave addresses.
4. **Document new caves in this file.** If you add a patch that uses a code cave, append its address range to the table above and update the summary.
5. **Prefer in-place single-instruction patches when possible.** If the fix is just forcing a constant or removing a branch, patch the single instruction directly. This avoids cave contention entirely.
6. **Claim the next free cave from the top.** The current top of the used cave space is `0x00392747`. If you need a new cave, check the stock binary for zero-filled executable space above that address and claim the next block. Document the exact start and end in your patch README and in this file.
