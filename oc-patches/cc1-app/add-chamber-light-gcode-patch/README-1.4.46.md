# Add chamber light gcode patch for 1.4.46

This documents the 1.4.46 port of `add-chamber-light-gcode-1.1.40.bsdiff`.
The generated patch file is:

```
add-chamber-light-gcode-1.4.46.bsdiff
```

The patch was built against `stock/app-1.4.46`.

- Find and label `cmd_m8212` and `cmd_m8213`
    - Find the `"M8212"` / `"M8213"` strings.
    - In `stock/app-1.4.46.hlil.txt`, the registration sites are:
```
000c3460  sub_a5a98(&var_48, "M8212")
000c3478  var_74 = sub_a5b38

000c3528  sub_a5a98(&var_48, "M8213")
000c3540  var_74 = sub_a5bf0
```
    - So the handler functions patched for 1.4.46 are:
```
M8212 -> sub_a5b38
M8213 -> sub_a5bf0
```

- Find and label `camera_light_control`
    - It is the function containing the string `"/dev/video0"`.
    - In 1.4.46 this is `sub_2f4878`.
    - The relevant open call appears at:
```
002f4894  open64("/dev/video0", 2, 0)
```

- Find and label `mainboard_light_control`
    - Find references to the camera light control in the existing camera-light switch logic.
    - In 1.4.46, the existing off/on paths show:
```
003628a0  sub_2f4878()
003628b0  if (sub_5158c()[0x86])
003628c0      sub_19700c(sub_5158c()[0x86], 0)

003636b4  sub_2f4878()
003636c4  if (sub_5158c()[0x86])
003636d4      sub_19700c(sub_5158c()[0x86], 1)
```
    - Therefore `sub_19700c` is the 1.4.46 `mainboard_light_control`.
    - The singleton/global used by the M8212/M8213 handlers is `data_4b1034`.
    - The mainboard-light object member is still at offset `0x218`.

- Patch the 1.4.46 command handlers
    - `sub_a5b38` starts at virtual address `0x000a5b38`, file offset `0x00095b38`.
    - `sub_a5bf0` starts at virtual address `0x000a5bf0`, file offset `0x00095bf0`.
    - Assemble this for `M8212` at `0x000a5b38`:

```
    push    {r4, r5, r6, lr}
    movw    r4, #0x1034
    movt    r4, #0x4b
    mov     r0, #0
    bl      sub_2f4878
    ldr     r3, [r4]
    cmp     r3, #0
    beq     .Lexit
    ldr     r0, [r3, #0x218]
    cmp     r0, #0
    beq     .Lexit
    mov     r1, #0
    bl      sub_19700c
.Lexit:
    pop     {r4, r5, r6, lr}
    bx      lr
```

    - Assemble this for `M8213` at `0x000a5bf0`:

```
    push    {r4, r5, r6, lr}
    movw    r4, #0x1034
    movt    r4, #0x4b
    mov     r0, #1
    bl      sub_2f4878
    ldr     r3, [r4]
    cmp     r3, #0
    beq     .Lexit
    ldr     r0, [r3, #0x218]
    cmp     r0, #0
    beq     .Lexit
    mov     r1, #1
    bl      sub_19700c
.Lexit:
    pop     {r4, r5, r6, lr}
    bx      lr
```

- Correct branch targets for 1.4.46
    - Because the branch encoding depends on the handler start address, verify these values after assembling:

```
// For M8212 at 0x000a5b38
bl 0x2f4878 -> camera_light_control
bl 0x19700c -> mainboard_light_control

// For M8213 at 0x000a5bf0
bl 0x2f4878 -> camera_light_control
bl 0x19700c -> mainboard_light_control
```

- Verification
    - Applying `add-chamber-light-gcode-1.4.46.bsdiff` to `stock/app-1.4.46` succeeds with `bspatch`.
    - The resulting binary changes only the two expected handler ranges.
    - The generated patch SHA256 is:

```
f575340747cd721379dc29fe5d2baeec23e588d81c997e442ae21215c35c0931
```
