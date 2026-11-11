@ Assemble with arm-none-eabi-as -march=armv7-a, then link at 0x4519d0.
.syntax unified
.arm
.global _start
_start:
    ldr r0, [r11, #0x4c]
    mov r1, r5
    ldr r3, [r0]
    ldr r3, [r3, #0x58]
    blx r3
    b 0x2794c8
