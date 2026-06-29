# fix-singlecolor-filament-selection binary patch for CC1 app 1.4.46

## Summary

`fix-singlecolor-filament-selection` fixes the 1.4.46 bug where single-color prints ignore the user-selected filament color and print with whatever is currently loaded.

When a single-color gcode is loaded, `app_colorsbox_explorer` detects all colors are identical and emits `SET_ALL_CHANNELS_SAME VALUE=1`. The `virtual_sdcard` handler (`sub_239698`) stores this flag at `*(obj + 0x214)`. Later, `cmd_M749` (`sub_27ada4` in `lite_multi_color`) reads the flag and **skips the entire unload/load cycle** with the log:

```
skip M749 (unload material): multi_color_connected=%d, all_channels_same=%d
```

The printer therefore never switches to the user-selected color — it just prints with the loaded filament.

This patch forces the `SET_ALL_CHANNELS_SAME` handler to always write `0`, so `cmd_M749` never skips. The printer will always respect the user-selected color for both slicer and touchscreen selection paths.

## Patch mechanism

**Target:** `sub_239698` in `virtual_sdcard.cpp`  
**Location:** `0x00239714` (VA)

Original instruction:

```asm
movne r0, #1    ; 0x13A00001
```

Patched instruction:

```asm
mov   r0, #0    ; 0xE3A00000
```

This is the conditional move inside the `SET_ALL_CHANNELS_SAME` handler that converts the parsed `VALUE` (0 or non-zero) to a boolean `0`/`1`. By forcing `r0 = 0` unconditionally, the subsequent `strb r0, [r6, #532]` (at `0x0023971c`) always stores `0`, making `all_channels_same` permanently false.

## Impact

- **Single-color prints:** Will now always do the unload/load cycle to respect the selected color.
- **Multi-color prints:** Unchanged — `all_channels_same` was already `0` for these.
- **Performance:** Single-color prints may take slightly longer (one extra unload/load cycle).
- **Safety:** No other logic is modified. The `all_channels_same` flag is only consumed by `cmd_M749` and the UI color display.

## Patch artifact

```text
fix-singlecolor-filament-selection-1.4.46.bsdiff
```

Generated against the stock 1.4.46 app binary:

```text
stock app sha256:      ae693f7dc096da1f734c2972694963286cba20dc8f6afac79f8468139b613129
patched app sha256:    dd967e9dddb77966e2828fa08ae67f8a7c68c7917e1adce4aa97de880b749895
bsdiff sha256:         5799db81be65f80d729b94ad77181d2810b4a66c37638bc6aeb0b1ac7fcd272d
```

## Verification

### Generation

```bash
oc-patches/cc1-app/fix-singlecolor-filament-selection/generate_patch.py \
  /home/paul/carbon/cc-firmware/stock/app-1.4.46 \
  /tmp/fix-singlecolor-filament-selection/app-1.4.46-fix-singlecolor

bsdiff \
  /home/paul/carbon/cc-firmware/stock/app-1.4.46 \
  /tmp/fix-singlecolor-filament-selection/app-1.4.46-fix-singlecolor \
  oc-patches/cc1-app/fix-singlecolor-filament-selection/fix-singlecolor-filament-selection-1.4.46.bsdiff
```

### Disassembly spot check

```asm
00239710  movw  r2, #17432      ; 0x4418
00239714  mov   r0, #0          ; patched: was movne r0, #1
00239718  movt  r3, #67         ; 0x43
0023971c  strb  r0, [r6, #532]  ; 0x214
00239720  movt  r2, #67         ; 0x43
```

### Application test

```bash
bspatch stock/app-1.4.46 /tmp/fix-singlecolor/bspatch-applied \
  oc-patches/cc1-app/fix-singlecolor-filament-selection/fix-singlecolor-filament-selection-1.4.46.bsdiff
sha256sum /tmp/fix-singlecolor/bspatch-applied
```

## Runtime validation

1. Boot patched firmware.
2. Load a single-color gcode with a color different from the currently loaded one.
3. Start the print.
4. Confirm the printer unloads the current filament and loads the selected color.
5. Confirm the print starts with the correct color.

## Regeneration script

`generate_patch.py` is included so this patch is reproducible and auditable. It validates:

- source app size
- source app SHA256
- exact original instruction bytes at `0x00239718`

If any check fails, it refuses to patch.
