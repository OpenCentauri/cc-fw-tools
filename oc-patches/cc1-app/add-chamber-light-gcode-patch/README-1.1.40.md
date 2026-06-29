# Add chamber light gcode patch

Binary ninja was used to create this patch

- Find and label cmd_m8212 & cmd_m8213
    - Find the "M8212"/"M8213" string and take the accompanying function (in my case set into var_74)
- Find and label camera_light_control
    - It's the only function that contains the string "/dev/video0"
- Find and label mainboard_light_control
    - Find references to camera_light control. Underneath the usage of it you can see a singleton pattern. After that a check:
```
002c23f8                                void* r0_19 = r3_5[0x86];
002c23f8                                
002c2400                                if (r0_19)
002c2408                                    mainboard_light_control(r0_19, 0);
```
- Go into cmd_m8212 or cmd_m8213, click at the function offset and open the assemble menu (Ctrl+Alt+A). Paste the following assembly

```
    push    {r4, r5, r6, lr}
    movw    r4, #0x54d4
    movt    r4, #0x3e
    mov     r0, #0
    bl      camera_light_control
    ldr     r3, [r4]
    cmp     r3, #0
    beq     .Lexit
    ldr     r0, [r3, #0x218]
    cmp     r0, #0
    beq     .Lexit
    mov     r1, #0
    bl      mainboard_light_control
.Lexit:
    pop     {r4, r5, r6, lr}
    bx      lr
```

- For me after pasting it messed up the jump references to camera_light_control and mainboard_light_control. You can press e to edit a specific line. See the below values for corrected offsets.

```
// For m8212
bl 0x1f1d4c -> camera_light_control
bl 0xe6474 -> mainboard_light_control

// For m8213
bl 0x1f1c94 -> camera_light_control
bl 0xe63bc -> mainboard_light_control
```