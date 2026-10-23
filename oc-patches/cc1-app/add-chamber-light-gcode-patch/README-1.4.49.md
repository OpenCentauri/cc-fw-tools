# Add chamber light gcode patch for 1.4.49

This documents the 1.4.49 port of `add-chamber-light-gcode-1.4.46.bsdiff`.
The generated patch file is:

```
add-chamber-light-gcode-1.4.49.bsdiff
```

The patch was built against `stock/app-1.4.49` (sha256 `1a899b50fc104a38fe3f77cf4988c810da6670f3d0cc457de5d876c49fd76843`).

- Find and label `cmd_m8212` and `cmd_m8213`
    - The `"M8212"` / `"M8213"` strings live in a packed 8-byte-stride gcode string table at `.rodata` VA `0x00416374`.. (no static pointers; referenced via interleaved `movw`/`movt` pairs).
    - Registration sites in 1.4.49:
```
000c36b0  movw r1, 0x63b4
000c36b4  movt r1, 0x41        ; "M8212"
...
000c36cc  movw r3, 0x5d98
000c36d4  movt r3, 0xa         ; handler 0x000a5d98

000c3778  movw r1, 0x63bc
000c377c  movt r1, 0x41        ; "M8213"
...
000c3794  movw r3, 0x5e50
000c379c  movt r3, 0xa         ; handler 0x000a5e50
```
    - So the handler functions patched for 1.4.49 are:
```
M8212 -> 0x000a5d98  (file offset 0x00095d98)
M8213 -> 0x000a5e50  (file offset 0x00095e50)
```
    - Stock handlers are identical no-op state queries: `ldrb r3,[r0]; cmp; bxne lr` then `ldr r0,[*0x4b27bc + 0x1c0]; b 0x23bed8` where `0x23bed8` is a getter (`ldrb r0,[r0,#0x1a2]; bx lr`).
    - Each stock handler continues past the query with a lazy-singleton-init tail (full extents roughly `0xa5d98..0xa5e4f` and `0xa5e50..0xa5f27`). The rewrite overwrites only the first 60 bytes; the tail bytes that follow become **unreachable dead code**. Verified safe: the only branches into either written span come from the handlers' own tails, which are themselves reachable only through the overwritten entries — no external branches or live data references enter the patched ranges.

- Find and label `camera_light_control`
    - It is the function containing the string `"/dev/video0"` (VA `0x0044df7c`).
    - In 1.4.49 this is `0x002f53d8` (the only code ref to the string is at `0x002f53ec`).

- Find and label `mainboard_light_control`
    - From the existing camera-light switch logic (callers of `0x002f53d8`):
```
00363c74  mov r0, #0
00363c78  bl 0x2f53d8          ; camera_light_control(0)
00363c7c  bl 0x515c4           ; singleton getter
00363c80  ldr r3, [r0, #0x218]
00363c84  cmp r3, #0
00363c88  beq skip
00363c8c  bl 0x515c4
00363c90  mov r1, #0
00363c94  ldr r0, [r0, #0x218]
00363c98  bl 0x1971cc          ; mainboard_light_control(obj, 0)

00364a88  mov r0, #1
00364a8c  bl 0x2f53d8          ; camera_light_control(1)
...
00364aa8  ldr r0, [r0, #0x218]
00364aac  bl 0x1971cc          ; mainboard_light_control(obj, 1)
```
    - Therefore `0x001971cc` is the 1.4.49 `mainboard_light_control`.
    - The singleton getter `0x000515c4` returns `*(void**)0x004b27bc` (allocates if null), so the handlers read the global directly like 1.4.46 did.
    - The mainboard-light object member is still at offset `0x218`.

- Patch the 1.4.49 command handlers
    - `M8212` at `0x000a5d98`, `M8213` at `0x000a5e50` (same body as 1.4.46, new addresses):

```
    push    {r4, r5, r6, lr}
    movw    r4, #0x27bc
    movt    r4, #0x4b
    mov     r0, #<val>          ; 0 for M8212, 1 for M8213
    bl      0x2f53d8            ; camera_light_control
    ldr     r3, [r4]
    cmp     r3, #0
    beq     .Lexit
    ldr     r0, [r3, #0x218]
    cmp     r0, #0
    beq     .Lexit
    mov     r1, #<val>
    bl      0x1971cc            ; mainboard_light_control
.Lexit:
    pop     {r4, r5, r6, lr}
    bx      lr
```

    - 15 instructions, 60 bytes each; the original handler bodies are longer (they include the lazy-init tails), so the rewritten body plus its `bx lr` never falls through into the orphaned tail bytes.

- Verification
    - Applying `add-chamber-light-gcode-1.4.49.bsdiff` to `stock/app-1.4.49` succeeds with `bspatch`.
    - The resulting binary changes exactly 112 bytes, all inside the two handler ranges (`0x00095d98`..`0x00095dd3` and `0x00095e50`..`0x00095e8b` file offsets); 4 of the 60 written bytes per site match stock (`push`, `movt r4`, `pop` and `bx` re-encoded identically).
    - Patched sites disassemble to the bodies above with `bl 0x2f53d8` / `bl 0x1971cc`.
    - The generated patch SHA256 is:

```
7d440f07259339312b73ae2d76921070095792b61da3c9cd74304ae3bf950034
```

- Byte guard
    - `patch.sh` runs `verify-1.4.49.py ./app before` before `bspatch` and `./app-patch after` after it. The guard checks only the spans the bsdiff writes; every other byte is ignored, so patch order against other app patches does not matter.
    - If the handler bodies are ever re-assembled, regenerate BOTH artifacts from the same pair so the guard cannot go stale:

```
python3 generate_patch.py <stock-app-1.4.49> <patched-app-1.4.49>
```
