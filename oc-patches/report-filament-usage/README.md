# Filament Usage JSON Patch

This patch extends the existing `PrintStats` JSON
structure to report filament usage in two forms:

- **Cumulative usage** (total extruded E position for the print, retractions included as negative values to preserve actual length)
- **Current usage delta** (current total minus last total, 250ms cycle)

The new values are reported as additional JSON key–value pairs built by the
patched JSON writer.

---

## Technical

- Hooks an existing **PrintStats JSON writer** and branches into a new
  function in unused executable space.
- The function...
  - Loads the current total E position from the motion planner via pointer offset.
  - Stores this value into an unused `.bss` location for later comparison.
  - Computes the delta between the current E position and the last stored
    E position (representing filament called over the last 250 ms).
  - Builds and reports two new JSON key–value pairs and injects them into the
    existing PrintStats output.
- The JSON keys themselves are **hex strings**, stored in the binary at fixed
  addresses and interpreted by the Home Assistant integration
  (TODO: push the HA fork that decodes these keys).

---

## Patched regions

All offsets below are **file offsets** (0-based) as seen in Binary Ninja.

### 1. Branch

- **Address**: `0x002DEB18` (also clobber `0x002DEB20`, redundant due to in-function registers)
- Patches an existing JSON writer site so that execution branches to the new
  asm, then returns back to the stock code path.

### 2. New assembly instructions

- **Range**: `0x00392680` – `0x00392747`
- Implements the new logic:

  - Saves/restores the necessary registers and VFP state.
  - Loads the current E‐axis commanded position from motion planner (Printer pointer in the transpiled cpp)
    and stores it into safe `.bss` locations.
  - Computes the 250 ms extrusion delta using the previous value stored in `.bss`.
  - Builds two additional JSON key–value pairs and calls the existing JSON helper
    used elsewhere in the firmware.
  - Returns back to the original JSON writer using the loaded address target.

### 3. String / key storage

Two constant strings (hex key representations) are stored near the code cave:

1. **Total filament usage key**

   - **Address**: `0x003925A0`
   - **Contents**: first key string (hex) used for **total filament usage**.

2. **Current delta usage key**

   - **Address**: `0x00392630`
   - **Contents**: second key string (hex) used for the **current 250 ms delta**.

These strings are referenced only by the new and are placed before it to preserve patchable 0-byte addresses.