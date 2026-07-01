# fix-noncanvas-load binary patch for CC1 app 1.4.46

## Summary

`fix-noncanvas-load` fixes the 1.4.46 `ELEGOO_LOAD_FILAMENT` crash seen on original / non-Canvas Centauri Carbon toolhead boards when the app strips all filament-related sensor sections from `/board-resource/printer.cfg`.

The patch is deliberately conservative:

- If the relevant Canvas-era sensor object exists, the original Elegoo code path still runs.
- If the object is absent, the code returns a safe default instead of dereferencing null.
- Only the final load-completion check treats a missing sensor as “loaded successfully.” This is scoped to that one state-machine decision so we do **not** globally pretend every absent switch is triggered.

Patch artifact:

```text
fix-noncanvas-load-1.4.46.bsdiff
```

Generated against the stock 1.4.46 app binary:

```text
stock app sha256: ae693f7dc096da1f734c2972694963286cba20dc8f6afac79f8468139b613129
patched app sha256: 7009bf28db12b87782efcb7da40ce302dbeb478d8b2cf188ac9575ab6c425a1f
bsdiff sha256: 274566704f06f95e5d886a982cee486fdbae380189c30d217d6cfacd082dbda5
```

## Why this patch exists

Firmware 1.4.46 changed filament load/unload handling from the simpler 1.1.40 flow into a sensor-driven `change_filament` state machine.

On Canvas / detected toolhead hardware, the app creates and enables switch sensor objects such as:

- `[filament_switch_sensor]`
- `[custom_filament_switch_sensor]`
- `[filament_wrap_sensor]`
- `[cut_sensor]`

On original / non-Canvas toolhead hardware, runtime observations showed the app strips those sections from `/board-resource/printer.cfg`. That means the singleton object pointers remain null even though the 1.4.46 load path still tries to use them.

### Live failure mode

Pressing **Load Filament** on `carbon` produced this sequence:

```text
cmd_ELEGOO_LOAD_FILAMENT zero_z not
Heater extruder approaching new target of 140.000
Heater extruder within range of 140.000
... XY homing ...
Heater extruder approaching new target of 230.000
Heater extruder within range of 230.000
Generating coredump for PID 1554
```

The screen looked stuck on step 1 / nozzle heating, but the nozzle had actually reached target. The GUI/app died immediately afterwards, before it could advance the UI.

Core registers confirmed the null dereference:

```text
SIGSEGV si_addr=0x3c
PC=0x00210fc8  sub_210fc8(void*)
LR=0x00146384  sub_146378(...) caller
R0=0x00000000
```

`sub_210fc8` starts with:

```asm
0x00210fc8  ldrb r3, [r0, #0x3c]
```

So `R0 == 0` crashes at address `0x3c`.

## Relevant object offsets

From the 1.4.46 decompilation and project notes:

```text
[filament_switch_sensor]        singleton index 0x8c, byte offset 0x230
[custom_filament_switch_sensor] singleton index 0x8d, byte offset 0x234
[filament_wrap_sensor]          singleton index 0x96, byte offset 0x258
[cut_sensor]                    singleton index 0x97, byte offset 0x25c
```

## Error cases and how they manifest

### Case 1: Load crashes after heating to 230°C

In `ELEGOO_LOAD_FILAMENT` (`sub_140394`), after heating and homing, the app waits on `[custom_filament_switch_sensor]`:

```asm
0x00140d08  ldr r0, [r3, #0x234]   ; [custom_filament_switch_sensor]
0x00140d0c  bl  sub_146378
```

On non-Canvas configs, `[custom_filament_switch_sensor]` does not exist, so `r0 == 0`.

`sub_146378` immediately calls `sub_210fc8(r0)`, which dereferences `r0 + 0x3c` and crashes.

**Patch behavior:** guard `sub_146378` at its entry. If `r0 == NULL`, return `0x0000`. In this state machine, high byte `0` makes the load path stop waiting and proceed into `ELEGOO_LOAD_FILAMENT_RETRY`.

### Case 2: Load feeds but then reports failure instead of success

`ELEGOO_LOAD_FILAMENT_RETRY` (`sub_13ac84`) eventually checks `[filament_switch_sensor]` to decide if the load succeeded:

```asm
0x0013b12c  ldr r0, [r3, #0x230]   ; [filament_switch_sensor]
0x0013b130  bl  sub_210fc8
...
0x0013b17c  bne success            ; low byte != 0 means loaded
```

A generic null-safe `sub_210fc8(NULL) => 0` avoids a crash, but would still make the final load result fail on non-Canvas boards because low byte `0` means “not loaded.”

**Patch behavior:** patch this specific final load-completion call site. If `[filament_switch_sensor]` is missing, synthesize `r0 = 1`, meaning “filament present,” and resume the original code. If the sensor exists, call the original sensor reader and preserve Canvas behavior.

This is intentionally scoped here only. We do **not** make every missing switch read return `1`.

### Case 3: Missing wrap sensor crashes or falsely fails load

`ELEGOO_LOAD_FILAMENT_RETRY` also checks `[filament_wrap_sensor]` at offset `0x258` via `sub_15baa4`:

```asm
0x0013b148  ldr r0, [r3, #0x258]   ; [filament_wrap_sensor]
0x0013b14c  bl  sub_15baa4
```

`sub_15baa4` dereferences its argument. On a stripped non-Canvas config, the wrap sensor object may be null.

**Patch behavior:** guard `sub_15baa4`. If `r0 == NULL`, return `0x0000`, meaning no wrap fault. If the object exists, run the original function.

### Case 4: Unload / cut sensor path has a related null-risk

`ELEGOO_UNLOAD_FILAMENT` registers to `sub_13b5b0`. It sends:

```gcode
CUT_OFF_FILAMENT ZERO_Z=%d
EXTRUDE_FILAMENT E=-60 F=<...> FAN_ON=0
```

Then it interacts with `[cut_sensor]` at offset `0x25c` / index `0x97`.

One read is explicitly guarded:

```asm
0x0013b858  ldr r0, [r3, #0x25c]
0x0013b85c  cmp r0, #0
0x0013b860  beq no_sensor_path
0x0013b864  bl  sub_210fc8
```

A later read assumes the object still exists:

```asm
0x0013b938  ldr r0, [r3, #0x25c]
0x0013b93c  bl  sub_210fc8
```

That is less likely to crash for a simply absent non-Canvas config because the first check skips the block, but it is the same unsafe pattern if the object table changes or an adjacent path reaches `sub_210fc8(NULL)`.

**Patch behavior:** globally guard `sub_210fc8`. Missing generic switch sensor returns `0x0000`, a harmless "not triggered / not active" default. This protects unload/cut paths and other similar unguarded switch-reader calls without changing real Canvas sensors.

### Case 5: Load retry loop reverses on non-Canvas after a previous operation

On original / non-Canvas hardware, `ELEGOO_LOAD_FILAMENT_RETRY` (`sub_13ac84`) can enter a state where the retry loop emits `G1 E-20` (reverse) instead of forward `G1 E2`. This happens after an operation such as an unload or print leaves a stale plug-detection timestamp in the `[plug_detect_sensor]` object at offset `0x50`. The retry loop compares that timestamp to the current time and, when it falls inside the "plug detected" window, it issues the reverse `G1 E-20` unclog move. The real non-Canvas toolhead has no plug-detection hardware, so the timestamp is stale state, not a real jam.

**Patch behavior:** hook the entry of `ELEGOO_LOAD_FILAMENT_RETRY`. If the non-Canvas hallmark (`[filament_switch_sensor]` at index `0x8c`) is missing, clear the `[plug_detect_sensor]` timestamp at offset `0x50` (and `0x54`) before the retry loop runs. Canvas systems, which have a real `[filament_switch_sensor]`, keep the original plug-detection behavior intact.

## What is patched

The patch installs four branch hooks and a compact trampoline block.

### Code cave

The trampoline block is written to an executable zero-filled cave inside the first `RX` load segment:

```text
VA:     0x00450100
Offset: 0x00440100
Size used: 0x48 bytes
Original bytes: 0x80 zero bytes validated by generate_patch.py
```

Although this address is in the `.rodata` section by section headers, it is covered by the first executable `PT_LOAD` segment (`R E`), so ARM branch targets there are executable at runtime on this firmware.

### Hook 1: `sub_146378` custom filament switch wrapper

Original:

```asm
0x00146378  push {r4, r5, lr}
```

Patched:

```asm
0x00146378  b 0x00450100
```

Trampoline:

```asm
0x00450100  cmp   r0, #0
0x00450104  bxeq  lr
0x00450108  push  {r4, r5, lr}
0x0045010c  b     0x0014637c
```

### Hook 2: `sub_15baa4` filament wrap sensor reader

Original:

```asm
0x0015baa4  push {r4, lr}
```

Patched:

```asm
0x0015baa4  b 0x00450110
```

Trampoline:

```asm
0x00450110  cmp   r0, #0
0x00450114  bxeq  lr
0x00450118  push  {r4, lr}
0x0045011c  b     0x0015baa8
```

### Hook 3: `sub_210fc8` generic switch reader

Original:

```asm
0x00210fc8  ldrb r3, [r0, #0x3c]
```

Patched:

```asm
0x00210fc8  b 0x00450120
```

Trampoline:

```asm
0x00450120  cmp   r0, #0
0x00450124  bxeq  lr
0x00450128  ldrb  r3, [r0, #0x3c]
0x0045012c  b     0x00210fcc
```

### Hook 4: final load-completion filament switch check

Original:

```asm
0x0013b12c  ldr r0, [r3, #0x230]
0x0013b130  bl  0x00210fc8
```

Patched:

```asm
0x0013b12c  b   0x00450130
0x0013b130  nop
```

Trampoline:

```asm
0x00450130  ldr   r0, [r3, #0x230]
0x00450134  cmp   r0, #0
0x00450138  moveq r0, #1
0x0045013c  beq   0x0013b134
0x00450140  bl    0x00210fc8
0x00450144  b     0x0013b134
```

### Hook 5: clear stale plug-detect state at the start of `ELEGOO_LOAD_FILAMENT_RETRY`

Original:

```asm
0x0013ac84  push {r4, r5, r6, r7, r8, r9, sl, fp, lr}
```

Patched:

```asm
0x0013ac84  b 0x00450148
```

Trampoline:

```asm
0x00450148  movw  r1, #0x1034
0x0045014c  movt  r1, #0x004b
0x00450150  ldr   r1, [r1]                ; data_4b1034
0x00450154  ldr   r2, [r1, #0x230]        ; [filament_switch_sensor]
0x00450158  cmp   r2, #0
0x0045015c  bne   0x00450178              ; Canvas -> skip reset
0x00450160  ldr   r2, [r1, #0x250]        ; [plug_detect_sensor]
0x00450164  cmp   r2, #0
0x00450168  beq   0x00450178              ; no sensor -> skip reset
0x0045016c  mov   r3, #0
0x00450170  str   r3, [r2, #0x50]
0x00450174  str   r3, [r2, #0x54]
0x00450178  push  {r4, r5, r6, r7, r8, r9, sl, fp, lr}
0x0045017c  b     0x0013ac88
```

## Why Canvas behavior should remain intact

Canvas/detected hardware creates the relevant sensor objects. For non-null objects:

- `sub_146378` executes the original function body after the preserved `push {r4, r5, lr}`.
- `sub_15baa4` executes the original function body after the preserved `push {r4, lr}`.
- `sub_210fc8` executes the original body after the preserved first `ldrb`.
- The final load-completion check still calls the original switch reader when `[filament_switch_sensor]` exists.

Therefore, Canvas sensors continue to control load success/failure, wrap fault handling, and cut/unload state.

## Verification performed

### Generation

```bash
oc-patches/cc1-app/fix-noncanvas-load/generate_patch.py \
  /home/paul/carbon/cc-firmware/stock/app-1.4.46 \
  /tmp/fix-noncanvas-load/app-1.4.46-fix-noncanvas-load

bsdiff \
  /home/paul/carbon/cc-firmware/stock/app-1.4.46 \
  /tmp/fix-noncanvas-load/app-1.4.46-fix-noncanvas-load \
  oc-patches/cc1-app/fix-noncanvas-load/fix-noncanvas-load-1.4.46.bsdiff
```

### Disassembly spot checks

Expected patched hooks:

```asm
0x00146378  b 0x00450100
0x0015baa4  b 0x00450110
0x00210fc8  b 0x00450120
0x0013b12c  b 0x00450130
0x0013b130  nop
```

Expected trampoline block:

```asm
0x00450100  cmp   r0, #0
0x00450104  bxeq  lr
0x00450108  push  {r4, r5, lr}
0x0045010c  b     0x0014637c
0x00450110  cmp   r0, #0
0x00450114  bxeq  lr
0x00450118  push  {r4, lr}
0x0045011c  b     0x0015baa8
0x00450120  cmp   r0, #0
0x00450124  bxeq  lr
0x00450128  ldrb  r3, [r0, #0x3c]
0x0045012c  b     0x00210fcc
0x00450130  ldr   r0, [r3, #0x230]
0x00450134  cmp   r0, #0
0x00450138  moveq r0, #1
0x0045013c  beq   0x0013b134
0x00450140  bl    0x00210fc8
0x00450144  b     0x0013b134
```

### Application test

```bash
bspatch stock/app-1.4.46 /tmp/fix-noncanvas-load/bspatch-applied \
  oc-patches/cc1-app/fix-noncanvas-load/fix-noncanvas-load-1.4.46.bsdiff
sha256sum /tmp/fix-noncanvas-load/bspatch-applied
```

The expected SHA256 is the patched app hash above.

## Runtime validation still needed

On original/non-Canvas hardware:

1. Boot patched firmware or run patched `/app/app` in a reversible test setup.
2. Press **Load Filament**.
3. Confirm it gets past `Heater extruder within range of 230.000` without coredumping.
4. Confirm retry/feed emits positive extrusion moves (`G1 E2 ...`).
5. Confirm final state reaches `cmd_ELEGOO_LOAD_FILAMENT_RETRY end` / busy reset rather than failure.
6. Press **Unload Filament**.
7. Confirm no coredump and heater shutdown (`M104 S0`) occurs.

On Canvas hardware:

1. Confirm boot logs still show `hardware_enabled set to true` for Canvas sensors.
2. Confirm load still follows the real sensor state when the filament switch object exists.
3. Confirm wrap/cut behavior remains active.

## Regeneration script

`generate_patch.py` is included so this patch is reproducible and auditable. It validates:

- source app size
- source app SHA256
- exact original hook bytes
- zero-filled code cave bytes

If any check fails, it refuses to patch.
