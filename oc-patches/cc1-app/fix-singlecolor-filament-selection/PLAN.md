# Plan: Fix Single-Color Filament Selection Bug (1.4.46)

## Bug Summary

When a single-color gcode is loaded, the firmware detects that all colors in the file are identical and sets `all_channels_same = 1`. This causes `cmd_M749` (unload material) to be **skipped** at print start. The result: the printer never switches to the user-selected filament color — it just prints with whatever is currently loaded.

**Affected paths:**
1. Touchscreen color selection for single-color prints
2. Slicer color selection for single-color prints

---

## Root Cause Analysis

### 1. Who sets `all_channels_same`?

**Function:** `sub_327168` in `app_colorsbox_explorer.cpp`  
**Location:** `00327168` (VA), around line 602414 in HLIL

This function iterates the color tree and compares:
- `__x->__offset(0x18).d` (color ID / slot)
- `__x->__offset(0x26).w` (channel / AMS slot)
- `__x->__offset(0x2c).d` (some other value)

If all elements are identical, it sets `r4 = 1`. Then it does:

```c
r2 = r4 != 0 ? 1 : r4;
sprintf(buf, "SET_ALL_CHANNELS_SAME VALUE=%d", r2);
```

This command is enqueued to the gcode command queue.

### 2. Who consumes `all_channels_same`?

**Function:** `sub_239698` in `virtual_sdcard.cpp`  
**Location:** `00239698` (VA), around line 434136 in HLIL

This is the command handler for `SET_ALL_CHANNELS_SAME`. It parses `VALUE=...` and writes:

```c
*(arg1 + 0x214) = value.b;   // all_channels_same flag
```

### 3. Who skips the color change?

**Function:** `cmd_M749` (`sub_27ada4`) in `lite_multi_color.cpp`  
**Location:** `0027ada4` (VA), around line 481786 in HLIL

```c
if (r0_1 != 3)  // not connected
    r3 = 1;     // skip

// ...

r3_2 = zx.d(*(r3_2 + 0x214));  // read all_channels_same

if (r3_2 != 0)
    // skip M749, log:
    // "skip M749 (unload material): multi_color_connected=%d, all_channels_same=%d"
```

The `M749` command is responsible for unloading the current filament and loading the selected one. When `all_channels_same` is true, it bails out.

### 4. What does `PRINT_START` do?

**Function:** `sub_13b5b0` in `change_filament.cpp`  
**Location:** `0013b5b0` (VA), around line 232474 in HLIL

This handles `PRINT_START` for `change_filament`. It sets `CHANGE_FILAMENT_SET_BUSY`, issues `CUT_OFF_FILAMENT`, `EXTRUDE_FILAMENT`, `M104 S0`, `M140 S0`, etc. It does **not** check `all_channels_same` or the currently loaded color. It relies on the upstream `M749` to have done the material switch.

### 5. Why does the bug only affect single-color prints?

For multi-color prints, `sub_327168` sees different colors in the tree and sets `r4 = 0`, so `all_channels_same = 0`. Then `M749` is not skipped, and the color changes work normally.

For single-color prints, the tree has one entry, all comparisons pass, `r4 = 1`, `all_channels_same = 1`, and `M749` is skipped. The firmware assumes "all channels are the same, so no need to change anything." But this assumption is wrong when the user explicitly selected a different single color.

---

## Path A: Prevent `all_channels_same` from being set when user selected a different color

### Idea
Patch `sub_327168` so that even if all gcode colors are the same, it does NOT set `all_channels_same = 1` if the user has selected a different color than the one in the gcode.

### Challenge
`sub_327168` is in `app_colorsbox_explorer.cpp` and only examines the gcode color tree. It does not have direct access to the user's selected color at that point. The user's color selection is stored in the UI state or in the `ColorMapping` / `target_channel` data structures.

### Possible Implementation
1. **Find the user's selected color** at the point where `sub_327168` is called. The UI state may have a global variable or a structure that holds the selected color.
2. **Compare the selected color** with the gcode's single color. If they differ, force `r4 = 0` so `all_channels_same = 0`.
3. **Patch location:** `00327400` (VA) where `r4 = 0` is set when differences are found. We could add an extra check before the `sprintf` to force `r2 = 0` if the user's selection differs.

### Pros
- Fixes the problem at the source — the flag is never set incorrectly.
- Minimal change to the execution flow after the flag is set.

### Cons
- Requires identifying the user's selected color in `app_colorsbox_explorer`, which may be in a different module or data structure.
- The `sub_327168` function is called from multiple places (slicer path, touchscreen path, copy file path). We need to make sure the patch applies correctly in all contexts.
- Risk: if the user's selected color is not available in all call paths, the patch may behave inconsistently.

---

## Path C: Patch `PRINT_START` or `cmd_M749` to force color change when loaded != selected

### Idea
Do not change how `all_channels_same` is set. Instead, at the point where the color change is actually executed, explicitly check whether the currently loaded color matches the selected color. If they differ, force the unload/load regardless of `all_channels_same`.

### Option C1: Patch `cmd_M749` to ignore `all_channels_same` when colors mismatch

In `cmd_M749` (`sub_27ada4`), we have access to:
- `var_2c` from `*(arg1 + 0x44)` — the active / target channel ID
- The `multi_color` object at `r3_2 + 0x214` — the `all_channels_same` flag

We could add logic:
1. Read the currently loaded channel ID from the multi_color object or the extruder state.
2. Compare it with `var_2c` (the target channel).
3. If they differ, set `r3 = 0` (do not skip) even if `all_channels_same` is true.

**Patch location:** `0027ae40` (VA) where `r3_2 = zx.d(*(r3_2 + 0x214))` is loaded. We could add a check after this to compare the active channel with the target channel.

### Option C2: Patch `sub_13b5b0` (`PRINT_START` in `change_filament`) to issue a forced load

Before the normal `PRINT_START` sequence, add a check:
1. Query the current active channel ID.
2. Query the target channel ID from the print job.
3. If they differ, issue `CHANGE_FILAMENT` or `LOAD_MATERIAL` commands explicitly.

**Patch location:** Early in `sub_13b5b0`, before the `CUT_OFF_FILAMENT` or `EXTRUDE_FILAMENT` commands.

### Pros
- Fixes the problem at the actual execution point, where the necessary state (active vs target channel) is already available.
- Does not depend on upstream color parsing logic.
- More robust: it works regardless of how `all_channels_same` was set.

### Cons
- Requires finding the "currently loaded channel" and "target channel" in the `lite_multi_color` or `change_filament` module.
- May need to add extra code/trampoline to perform the comparison.
- Risk: if the active channel query is not reliable or if the target channel is not set yet at this point, the patch could fail or cause unnecessary filament changes.

---

## Recommendation

**Path C (Option C1: Patch `cmd_M749`) is the most likely to work without negative impacts.**

### Reasoning

1. **Data availability:** `cmd_M749` already has the target channel ID (`var_2c`). The `multi_color` object is also available in the same function. We can query the currently loaded channel ID from the same object or a related global.

2. **Surgical precision:** We only modify the skip logic in `cmd_M749`. We don't change `all_channels_same` semantics, which might affect other parts of the firmware (e.g., the slicer preview, the UI color display, etc.).

3. **Minimal blast radius:** The patch only affects the unload/load decision. If the active channel already matches the target, the behavior is unchanged. If they differ, we force the change.

4. **No upstream dependencies:** We don't need to chase down where the user's selected color is stored in `app_colorsbox_explorer` or the UI layer.

### Implementation Sketch for Option C1

1. **Find the active channel ID:** In `cmd_M749`, the `multi_color` object is at `r3_2` (or `data_4b1034`). We need to find the offset of the active/loaded channel ID. The log string `"get now active channel id failed"` suggests there is already code that queries it. We can find that offset and reuse it.

2. **Compare with target:** The target channel ID is in `var_2c` (fetched from `*(arg1 + 0x44)`). If `active != target`, we should not skip.

3. **Patch the skip logic:**
   - Current: `if (r3_2 != 0) skip;`
   - New: `if (r3_2 != 0 && active_channel == target_channel) skip;`
   - Or: `if (r3_2 != 0) { if (active_channel != target_channel) r3_2 = 0; }`

4. **Trampoline location:** Use the existing patch infrastructure (trampolines at `0x450100` or similar) to inject the comparison code.

### Next Steps

1. Confirm the exact offset of `active_channel_id` in the `multi_color` object or the global state.
2. Verify the exact assembly instructions around `0027ae40` in `cmd_M749` to plan the patch.
3. Write the patch using the existing `patch.toml` / `patch.sh` / `generate_patch.py` framework.
4. Test on both touchscreen and slicer single-color prints.

---

## Alternative: Quick & Dirty Workaround

If a full patch is too risky, a simpler workaround exists:

**Patch `sub_327168` to always emit `SET_ALL_CHANNELS_SAME VALUE=0` regardless of the color tree.**

This effectively disables the `all_channels_same` optimization entirely. The printer will always do `M749` unload/load at print start.

- **Pros:** Trivial to implement, guaranteed to fix both cases.
- **Cons:** Every single-color print will do an unnecessary unload/load cycle, adding time and wear. Might be annoying for users who print the same color repeatedly.

---

*Document generated from 1.4.46 HLIL analysis.*
