@ CC1 stock-1.4.49 SDCP Status.PrintInfo filament usage.
@ Based on harpua555's original patch, OpenCentauri/cc-fw-tools PR #40.
@ Cave 0x4518d0; hook 0x36d310; r8 is the PrintInfo JSON object.
.syntax unified
.arm
.text
.global _start
.equ JSON_HELPER, 0x2c9b80
.equ PRINTER_PTR, 0x4b27bc
.equ KEY_TOTAL, 0x4519a0
.equ KEY_DELTA, 0x4519b0
.equ BSS_PREV, 0x522f08
.equ BSS_DELTA, 0x522f10
.equ RESUME, 0x36d320

_start:
    push {r0-r7}
    vpush {d12}
    @ Replay the overwritten TotalLayer instructions; low r1 is set pre-hook.
    movt r1, #0x45
    vmov s15, r3
    vcvt.f64.u32 d0, s15
    mov r0, r8
    movw ip, #:lower16:JSON_HELPER
    movt ip, #:upper16:JSON_HELPER
    blx ip

    @ Printer -> PrintStats -> accumulated, flow-normalized filament_used.
    movw r0, #:lower16:PRINTER_PTR
    movt r0, #:upper16:PRINTER_PTR
    ldr r0, [r0]
    ldr r0, [r0, #0xf8]
    add r0, r0, #0x1c0
    ldrd r2, [r0]
    vmov d0, r2, r3
    movw r5, #:lower16:BSS_PREV
    movt r5, #:upper16:BSS_PREV
    ldrd r6, [r5]
    vmov d12, r6, r7
    strd r2, [r5]
    vsub.f64 d0, d0, d12
    vmov r6, r7, d0
    movw r5, #:lower16:BSS_DELTA
    movt r5, #:upper16:BSS_DELTA
    strd r6, [r5]

    mov r0, r8
    movw r1, #:lower16:KEY_TOTAL
    movt r1, #:upper16:KEY_TOTAL
    movw r5, #:lower16:BSS_PREV
    movt r5, #:upper16:BSS_PREV
    ldrd r6, [r5]
    vmov d0, r6, r7
    movw ip, #:lower16:JSON_HELPER
    movt ip, #:upper16:JSON_HELPER
    blx ip

    mov r0, r8
    movw r1, #:lower16:KEY_DELTA
    movt r1, #:upper16:KEY_DELTA
    movw r5, #:lower16:BSS_DELTA
    movt r5, #:upper16:BSS_DELTA
    ldrd r6, [r5]
    vmov d0, r6, r7
    movw ip, #:lower16:JSON_HELPER
    movt ip, #:upper16:JSON_HELPER
    blx ip
    vpop {d12}
    pop {r0-r7}
    b RESUME
