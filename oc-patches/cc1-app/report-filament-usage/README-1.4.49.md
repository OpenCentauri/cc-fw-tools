# Filament Usage JSON Patch (CC1 1.4.49)

## Purpose
Extends the SDCP status JSON with two fields consumed by the Home Assistant
integration:

- `TotalExtrusion` — cumulative extruded E position (double)
- `CurrentExtrusion` — per-status-cycle delta (current total minus previous)

Key strings are byte-identical to the 1.4.46 patch (HA contract).

## Why (stock check)
Stock 1.4.49's status JSON writer (VA `0x37f6fc`) emits layer/progress/speed
keys but no filament usage. The stock `filament_used` string only appears in
gcode-file metadata parsing, never in status JSON.

## Sites (1.4.49)

| Item | VA | Notes |
|---|---|---|
| Hook site | `0x0037f9ec` (file `0x0036f9ec`) | 12B `movw r1,#0x96d0; movt r1,#0x45; vcvt.f64.u32 d0,s15` → `movw ip,#0x18d0; movt ip,#0x45; bx ip` |
| Injected fn cave | `0x004518d0` | 196 bytes, rodata zero run (R-E LOAD → executable) |
| Key strings | `0x004519a0` / `0x004519b0` | `TotalExtrusion\0` / `CurrentExtrusion\0` |
| JSON double helper | `0x002c9b80` | r0=json obj (`r4` at hook), r1=key, d0=value |
| E-position path | `[[0x4b27bc]+0xf8]+0x1c0` | printer global → motion planner → E double |
| bss state | `0x004b4788` / `0x004b4790` | prev/delta doubles; runtime-zero (no file backing — not byte-guarded) |
| Resume | `0x0037f9fc` | skips stock TotalLayer `bl` (cave replays it — no double-emit) |

The cave fn: replay triplet → emit TotalLayer → load E → update prev/delta
bss → emit both new keys → resume. Register hygiene: `push {r0-r7}` +
`vpush {d12}`/`vpop`; `r4` (json obj) and `s15` (TotalLayer value, loaded
pre-hook) are consumed before any helper call.

Idle path (`0x37f858`, constant 0.0) deliberately unhooked — parity with 1.4.46.

## Files
- `injected-1.4.49.S` — injected function source (source of truth)
- `patch.py` — applies hook + blob + key strings (byte-guarded, cave/key regions zero-checked)
- `patch.sh` — dispatches 1.4.49 to `patch.py`; older versions keep the bsdiff path

## Rebuilding the blob

```bash
arm-none-eabi-as -march=armv7-a -mfpu=vfpv3 -o injected-1.4.49.o injected-1.4.49.S
arm-none-eabi-ld -Ttext=0x4518d0 -o injected-1.4.49.elf injected-1.4.49.o
arm-none-eabi-objcopy -O binary injected-1.4.49.elf injected-1.4.49.bin
xxd -p injected-1.4.49.bin | tr -d '\n'   # -> FN hex in patch.py
```

## Verification
- Pristine stock: hook shows `movw ip,#0x18d0; movt ip,#0x45; bx ip`; cave head
  shows `push {r0-r7}; vpush {d12}; movw r1,#0x96d0; …`; keys present; re-run refuses.
- Behavior: status JSON includes `TotalExtrusion`/`CurrentExtrusion` while printing.

## Accepted risks
- **No unwind coverage:** the cave has no `.ARM.exidx` entry; a C++ exception
  thrown with the PC inside the injected fn (the JSON helper's allocator can
  throw `bad_alloc`) terminates instead of unwinding. Accepted — same shape as
  the shipped 1.4.46 patch; the allocation is a ~48-byte JSON node.
- **bss scratch is not byte-guardable** (no file backing); unreferenced in a
  ±0x100 static scan, but base+index accesses are invisible to that scan —
  same accepted risk as 1.4.46.
