# TEMPERATURE_WAIT Box Sensor Patch (CC1 1.4.49)

## Purpose
Adds chamber (`box`) temperature support to `TEMPERATURE_WAIT`. The patch
diverts only when `SENSOR` is not a stock heater:

```
M400
TEMPERATURE_WAIT SENSOR=box MINIMUM=45 MAXIMUM=60
M400
```

waits (10ms `usleep` loop, UI stays responsive) until chamber temp is within
range, then continues. Chamber temp comes from a `simple_bus_request` for
`srv_state` (double at state offset `+0x48`).

## ⚠ Behavior fix vs 1.4.46
The 1.4.46 trampoline sent **non-box** sensors straight to the stock epilogue,
silently breaking `TEMPERATURE_WAIT SENSOR=<real heater>`. The 1.4.49
trampoline re-executes the displaced clock call (`bl 0xed8d8`) and resumes the
stock handler (`0x177d8c`) for non-box sensors — stock heater behavior is
preserved, matching the documented 1.1.40 intent.

## Sites (1.4.49)

| Item | VA | Notes |
|---|---|---|
| Hook site | `0x00177d88` (file `0x00167d88`) | `bl 0xed8d8` (`d2d6fdeb`) → `b 0x4517f0` (`98660bea`) |
| Trampoline cave | `0x004517f0` | 216 bytes, rodata zero run (R-E LOAD → executable) |
| Stock epilogue resume | `0x00177f98` | box wait complete |
| Stock handler resume (non-box fix) | `0x00177d8c` | instruction after the hook |
| `simple_bus_request` | `0x0002b874` | r0=name, r3=out; 0 on match |
| `"srv_state"` string | `0x004440fc` | |
| `usleep` PLT | `0x0001c544` | |

Hook invariants (verified in stock 1.4.49, same as 1.4.46): `d11`=MINIMUM,
`d12`=MAXIMUM live at hook; SENSOR `std::string` char* at handler `[sp+0x10]`
(trampoline reads `[sp+0xf0]` after `sub sp,#0xe0`); state struct 0xd0 bytes.

## Files
- `trampoline-1.4.49.S` — trampoline source (source of truth)
- `patch.py` — applies hook + writes the assembled blob (byte-guarded, cave zero-checked)
- `patch.sh` — dispatches 1.4.49 to `patch.py`; 1.1.40/1.4.46 keep the bsdiff path

## Rebuilding the blob

```bash
arm-none-eabi-as -march=armv7-a -mfpu=vfpv3 -o trampoline-1.4.49.o trampoline-1.4.49.S
arm-none-eabi-ld -Ttext=0x4517f0 -o trampoline-1.4.49.elf trampoline-1.4.49.o
arm-none-eabi-objcopy -O binary trampoline-1.4.49.elf trampoline-1.4.49.bin
xxd -p trampoline-1.4.49.bin | tr -d '\n'   # -> TRAMPOLINE hex in patch.py
```

## Verification
- Pristine stock: hook disassembles to `b 0x4517f0`; cave head shows
  `sub sp,#0xe0; vstr d11,[sp,#0xd0]; vstr d12,[sp,#0xd8]; ldr r0,[sp,#0xf0]`;
  re-run refuses; cave-zero check refuses a colliding cave.
- Behavior: `TEMPERATURE_WAIT SENSOR=box MINIMUM=45 MAXIMUM=60` holds gcode
  until chamber is in range; `TEMPERATURE_WAIT SENSOR=heater_bed ...` (stock
  heater) still works (the 1.4.49 fix).

## Accepted risks
- **No unwind coverage:** the cave has no `.ARM.exidx` entry; a C++ exception
  thrown with the PC inside the trampoline (e.g. allocator `bad_alloc` deep in
  `simple_bus_request`) terminates instead of unwinding. Accepted — same shape
  as the shipped 1.4.46 patch; allocation-failure paths here are effectively
  unreachable on-device.
- **NaN waits forever:** an unordered `vcmpe` result (NaN chamber temp)
  satisfies `bhi` → infinite wait. Same as shipped 1.4.46; the M400 guard is
  the mitigation.
