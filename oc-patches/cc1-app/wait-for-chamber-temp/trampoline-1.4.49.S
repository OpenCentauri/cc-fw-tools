@ wait-for-chamber-temp trampoline for CC1 1.4.49
@ Cave VA: 0x4517f0 (rodata zero run, R-E LOAD segment — executable)
@ Hook: 0x177d88 `bl 0xed8d8` -> `b 0x4517f0`
@ Port of the 1.4.46 trampoline (0x450200) with the non-box fallthrough FIX:
@ non-box sensors re-execute the displaced clock call and resume the stock
@ handler instead of jumping straight to the epilogue (1.4.46 broke stock
@ heater TEMPERATURE_WAIT).
@
@ Build:  arm-none-eabi-as -march=armv7-a -mfpu=vfpv3 -o trampoline-1.4.49.o trampoline-1.4.49.S
@         arm-none-eabi-ld -Ttext=0x4517f0 -o trampoline-1.4.49.elf trampoline-1.4.49.o
@         arm-none-eabi-objcopy -O binary trampoline-1.4.49.elf trampoline-1.4.49.bin
.syntax unified
.arm
.text
.global _start

.equ BUS_REQUEST, 0x2b874      @ simple_bus_request (r0=name, r1, r2, r3=out; 0 on match)
.equ SRV_STATE,   0x4440fc     @ "srv_state" string
.equ USLEEP,      0x1c544      @ usleep PLT
.equ EPILOGUE,    0x177f98     @ stock handler epilogue (box done)
.equ CLOCK_CALL,  0xed8d8      @ displaced bl target (returns double in d0)
.equ STOCK_RESUME, 0x177d8c    @ instruction after the hook

_start:
    sub  sp, sp, #0xe0
    vstr d11, [sp, #0xd0]      @ spill MIN/MAX (live in regs at hook time)
    vstr d12, [sp, #0xd8]
    ldr  r0, [sp, #0xf0]       @ SENSOR char* = handler [sp+0x10]

    ldrb r1, [r0]
    cmp  r1, #0x62             @ 'b'
    bne  not_box
    ldrb r1, [r0, #1]
    cmp  r1, #0x6f             @ 'o'
    bne  not_box
    ldrb r1, [r0, #2]
    cmp  r1, #0x78             @ 'x'
    bne  not_box
    ldrb r1, [r0, #3]
    cmp  r1, #0
    bne  not_box

loop:
    movw r0, #:lower16:SRV_STATE
    movt r0, #:upper16:SRV_STATE
    mov  r1, #0
    mov  r2, #0
    mov  r3, sp                @ out: 0xd0-byte state struct on trampoline frame
    movw ip, #:lower16:BUS_REQUEST
    movt ip, #:upper16:BUS_REQUEST
    blx  ip
    cmp  r0, #0
    bne  req_failed

    vldr d8, [sp, #0x48]       @ chamber temp (double at state+0x48)
    vldr d11, [sp, #0xd0]      @ MIN
    vldr d12, [sp, #0xd8]      @ MAX
    add  sp, sp, #0xe0
    vcmpe.f64 d11, d8
    vmrs APSR_nzcv, fpscr
    bhi  wait_more             @ MIN > temp -> keep waiting
    vcmpe.f64 d12, d8
    vmrs APSR_nzcv, fpscr
    blt  wait_more             @ MAX < temp -> keep waiting
    movw ip, #:lower16:EPILOGUE
    movt ip, #:upper16:EPILOGUE
    bx   ip                    @ in range -> stock epilogue

wait_more:
    movw r0, #10000
    movw ip, #:lower16:USLEEP
    movt ip, #:upper16:USLEEP
    blx  ip
    b    _start                @ re-enter trampoline (re-sub sp, re-read sensor)

req_failed:
    add  sp, sp, #0xe0
    movw r0, #10000
    movw ip, #:lower16:USLEEP
    movt ip, #:upper16:USLEEP
    blx  ip
    b    _start

not_box:                       @ 1.4.49 fix: keep stock heater behavior
    add  sp, sp, #0xe0
    mov  r0, sl                @ restore bl argument (stock: mov r0, sl @ 0x177d80)
    bl   CLOCK_CALL            @ re-execute displaced clock call
    b    STOCK_RESUME
