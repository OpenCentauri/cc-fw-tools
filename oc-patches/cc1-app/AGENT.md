# CC1 App Binary Patch Map for Firmware 1.4.46

> **WARNING:** Any new patch must not overlap with existing code caves, branch hooks, or data strings. Overlapping patches will silently corrupt each other in the full patch chain. Always verify the full `patch_planner.py` build chain before committing a new patch.

## Executive Summary

The 1.4.46 app binary uses three **injected code caves** (new trampolines written into zero-filled executable space) and several **in-place patches** (single instructions or existing function bodies modified directly). The three caves are:

| Cave Address | Used By | Size | End |
|--------------|---------|------|-----|
| `0x00450100` | `fix-noncanvas-load` | 0x48 bytes | `0x00450147` |
| `0x00450200` | `wait-for-chamber-temp` | 0xd8 bytes | `0x004502d7` |
| `0x00450a00` | `report-filament-usage` | 0xc4 bytes | `0x00450ac3` |

There are **no other code caves** in the current 1.4.46 patch set. The next available zero-filled region after `0x00450ac3` is unallocated; any new patch needing a cave should claim from there and document it here.

## Patch-by-Patch Breakdown

### `fix-noncanvas-load` (1.4.46 only)
**Type:** Branch-hook trampoline cave
**Cave:** `0x00450100` — `0x00450147` (0x48 bytes, padded to 0x80)
**Branch hooks:**
- `0x00146378` → `0x00450100` (was `push {r4,r5,lr}`)
- `0x0015baa4` → `0x00450110` (was `push {r4,lr}`)
- `0x00210fc8` → `0x00450120` (was `ldrb r3, [r0, #0x3c]`)
- `0x0013b12c` → `0x00450130` (was `ldr r0, [r3, #0x230]`)

### `wait-for-chamber-temp` (1.4.46)
**Type:** Branch-hook trampoline cave
**Cave:** `0x00450200` — `0x004502d7` (0xd8 bytes)
**Branch hook:**
- `0x00177bc8` → `0x00450200` (was `bl sub_ed718`)
**Note:** This was relocated from `0x00450100` to avoid collision with `fix-noncanvas-load`. Never move it back.

### `report-filament-usage` (1.4.46)
**Type:** Branch-hook trampoline cave + data strings + BSS scratch
**Cave:** `0x00450a00` — `0x00450ac3` (0xc4 bytes)
**Branch hook:**
- `0x0036bf38` → `0x00450a00` (replaced `movt/vmov/vcvt` sequence)
**Data strings:**
- `0x00450920` — total key string
- `0x00450980` — current delta key string
**BSS scratch:**
- `0x004b4788` — previous total
- `0x004b4790` — current delta

### `fix-singlecolor-filament-selection` (1.4.46 only)
**Type:** Single-instruction in-place patch
- `0x00239714`: `movne r0, #1` → `mov r0, #0` (0x13A00001 → 0xE3A00000)
**No cave used.**

### `add-chamber-light-gcode-patch` (1.4.46)
**Type:** Existing function body rewrite
- `0x000a5b38` — `M8212` handler `sub_a5b38` rewritten in-place
- `0x000a5bf0` — `M8213` handler `sub_a5bf0` rewritten in-place
**No cave used.**

### `ota-updates-patch` (1.4.46)
**Type:** Data string replacement
- `0x0044738c` — URL string patched in `.rodata`
- `0x002c275c`, `0x002f88ec`, `0x002f8930`, `0x002f9ac0`, `0x002f9af8` — related code points
**No cave used.**

### `allow-api-during-printing-patch` (1.4.46)
**Type:** In-place binary patch
- `0x00370738`, `0x003707f8`, `0x00370a64`
**No cave used.**

### `allow-uploads-during-printing-patch` (1.4.46)
**Type:** In-place binary patch
- `0x003698a4`, `0x003698dc`, `0x00369904`, `0x00369e74`
**No cave used.**

### `block-connectivity-check-patch` (1.4.46)
**Type:** In-place binary patch
- `0x002942b8`, `0x002942f8`, `0x0029430c`, `0x002a2ea4`, `0x002a3684`
- `0x002f848c`, `0x002f84b4`, `0x002f84cc`, `0x002f84e0`, `0x003071ec`, `0x003079cc`
**No cave used.**

### `disable-exhaust-fan-patch` (1.4.46)
**Type:** In-place binary patch
- `0x0035d508`, `0x0035d50c`, `0x0035d5d4`, `0x0035d5d8`
**No cave used.**

### `do-not-block-z-offset-adjust-patch` (1.4.46)
**Type:** In-place binary patch
- `0x00341700`, `0x0034b8c4`, `0x0034b8dc`, `0x0034be8c`, `0x0034bfac`
**No cave used.**

### `set-firmware-version-patch`
**Not enabled for 1.4.46** (`compatible_versions = ["1.1.40"]`). No 1.4.46 addresses.

## Collision Rules for New Patches

1. **Never reuse an existing cave.** Caves are zero-filled only in the stock binary; once a patch writes to it, the bytes are consumed.
2. **Never place a new cave inside another patch's cave boundary.** This was the root cause of the `wait-for-chamber-temp` / `fix-noncanvas-load` crash (both tried to use `0x00450100`).
3. **Always run `patch_planner.py 1.4.46 --dry-run` after adding a new patch.** It shows the full ordered patch chain. Then build with `sudo ./build.sh 1.4.46` and disassemble the final app to verify all cave addresses.
4. **Document new caves in this file.** If you add a patch that uses a code cave, append its address range to the table above and update the summary.
5. **Prefer in-place single-instruction patches when possible.** If the fix is just forcing a constant or removing a branch, patch the single instruction directly (like `fix-singlecolor-filament-selection`). This avoids cave contention entirely.
6. **Claim the next free cave from the top.** The current top of the used cave space is `0x00450ac3`. If you need a new cave, check the stock binary for zero-filled executable space above that address and claim the next block. Document the exact start and end in your patch README and in this file.
