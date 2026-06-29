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

### 4. Commented assembly instructions

```.arm
push    {r0, r1, r2, r3}             @ Save registers r0-3 to stack in case they are needed on return (preserve state)
movw    r0, #0x54d4                  @ Load lower 16 bits of g_Printer address
movt    r0, #0x3e                    @ Load upper 16 bits: r0 = 0x3e54d4 (g_Printer global)
ldr     r0, [r0]                     @ Deref g_Printer to get obj address (runtime: 0xA7A00470)
ldr     r0, [r0, #0xf8]              @ Load motion planner object from obj at offset 0xf8
add     r0, r0, #0x1c0               @ Add offset 0x1c0 to reach E-axis position field
ldrd    r2, r3, [r0]                 @ Load 64-bit double (E position in mm) into r2:r3 regs
vmov    d0, r2, r3                   @ Move the 64-bit value from int regs to FPU double reg d0
movw    r3, #0x4c80                  @ Load lower 16 bits of output buffer address
movt    r3, #0x3e                    @ Load upper 16 bits: r3 = 0x3e4c80 (JSON output buffer)
vstr    d0, [r3]                     @ Store E position double to output buffer (gets included in printer status JSON)
pop     {r0, r1, r2, r3}             @ Restore registers r0-3 from stack (return to state)
movw    r12, #0xea64                 @ Load lower 16 bits of return address
movt    r12, #0x2d                   @ Load upper 16 bits: r12 = 0x2dea64 (original code continuation)
bx      r12                          @ Branch/return to original execution address```