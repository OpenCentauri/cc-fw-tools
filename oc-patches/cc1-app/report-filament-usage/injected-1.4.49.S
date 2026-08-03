@ report-filament-usage injected function for CC1 1.4.49
@ Cave VA: 0x4518d0 (rodata zero run, R-E LOAD segment — executable)
@ Hook: 0x37f9ec 12B (movw r1,#0x96d0; movt r1,#0x45; vcvt.f64.u32 d0,s15)
@       -> movw ip,#0x18d0; movt ip,#0x45; bx ip
@ Port of the 1.4.46 injected fn (0x450a00). Emits TotalLayer (replayed stock
@ call), then TotalExtrusion (cumulative E) and CurrentExtrusion (per-cycle
@ delta) via the stock JSON double helper.
@
@ Key strings (written by patch.py): "TotalExtrusion\0" @ 0x4519a0,
@ "CurrentExtrusion\0" @ 0x4519b0 — exact 1.4.46 strings (HA integration
@ contract).
@
@ Build:  arm-none-eabi-as -march=armv7-a -mfpu=vfpv3 -o injected-1.4.49.o injected-1.4.49.S
@         arm-none-eabi-ld -Ttext=0x4518d0 -o injected-1.4.49.elf injected-1.4.49.o
@         arm-none-eabi-objcopy -O binary injected-1.4.49.elf injected-1.4.49.bin
.syntax unified
.arm
.text
.global _start

.equ JSON_HELPER, 0x2c9b80     @ (r0=json obj, r1=key, d0=value)
.equ PRINTER_PTR, 0x4b27bc     @ global printer object ptr
.equ KEY_TOTAL,   0x4519a0     @ "TotalExtrusion\0"
.equ KEY_DELTA,   0x4519b0     @ "CurrentExtrusion\0"
.equ BSS_PREV,    0x4b4788     @ previous E total (double, runtime-zero)
.equ BSS_DELTA,   0x4b4790     @ last computed delta (double, runtime-zero)
.equ RESUME,      0x37f9fc     @ instruction after stock TotalLayer bl

_start:
    push {r0-r7}
    vpush {d12}

    @ --- replay clobbered triplet + emit TotalLayer (stock behavior) ---
    movw r1, #0x96d0           @ "TotalLayer" key (stock)
    movt r1, #0x45
    vcvt.f64.u32 d0, s15       @ s15 = TotalLayer value (loaded pre-hook)
    mov  r0, r4                @ json obj
    movw ip, #:lower16:JSON_HELPER
    movt ip, #:upper16:JSON_HELPER
    blx  ip

    @ --- current E total: [[PRINTER_PTR]+0xf8]+0x1c0 (double) ---
    movw r0, #:lower16:PRINTER_PTR
    movt r0, #:upper16:PRINTER_PTR
    ldr  r0, [r0]
    ldr  r0, [r0, #0xf8]       @ motion planner
    add  r0, r0, #0x1c0
    ldrd r2, [r0]
    vmov d0, r2, r3            @ cur

    @ --- delta bookkeeping ---
    movw r5, #:lower16:BSS_PREV
    movt r5, #:upper16:BSS_PREV
    ldrd r6, [r5]              @ prev
    vmov d12, r6, r7
    strd r2, [r5]              @ prev = cur
    vsub.f64 d0, d0, d12       @ delta = cur - prev
    vmov r6, r7, d0
    movw r5, #:lower16:BSS_DELTA
    movt r5, #:upper16:BSS_DELTA
    strd r6, [r5]              @ store delta

    @ --- emit TotalExtrusion (cumulative) ---
    mov  r0, r4
    movw r1, #:lower16:KEY_TOTAL
    movt r1, #:upper16:KEY_TOTAL
    movw r5, #:lower16:BSS_PREV
    movt r5, #:upper16:BSS_PREV
    ldrd r6, [r5]
    vmov d0, r6, r7
    movw ip, #:lower16:JSON_HELPER
    movt ip, #:upper16:JSON_HELPER
    blx  ip

    @ --- emit CurrentExtrusion (delta) ---
    mov  r0, r4
    movw r1, #:lower16:KEY_DELTA
    movt r1, #:upper16:KEY_DELTA
    movw r5, #:lower16:BSS_DELTA
    movt r5, #:upper16:BSS_DELTA
    ldrd r6, [r5]
    vmov d0, r6, r7
    movw ip, #:lower16:JSON_HELPER
    movt ip, #:upper16:JSON_HELPER
    blx  ip

    vpop {d12}
    pop  {r0-r7}
    b    RESUME
