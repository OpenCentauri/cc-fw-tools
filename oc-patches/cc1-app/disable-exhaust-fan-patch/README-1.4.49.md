# Disable Exhaust Fan Auto-On (CC1 1.4.49)

## Purpose
Stock 1.4.49 automatically drives the chamber exhaust fan from chamber
temperature during a print (periodic app-top handler VA `0x35e388`, fan helper
`0x342784` containing `real_fan_speed = %d`). This patch NOPs the two branches
that enter the fan-control block, skipping the whole block — parity with the
1.1.40/1.4.46 patches.

## Sites (1.4.49)

| Path | Site VA | File offset | Stock bytes (LE) | Stock instr | Patched |
|---|---|---|---|---|---|
| first print-active path | `0x0035e920` | `0x0034e920` | `3000001a` | `bne 0x35e9e8` | `nop` |
| second print-active path | `0x0035e938` | `0x0034e938` | `3200001a` | `bne 0x35ea08` | `nop` |

The fan block (`0x35e9e8`–`0x35ea17`) becomes unreachable; both fall-through
paths continue at `0x35e924`/`0x35e93c`.

## Mechanism
`patch.py` (via `patch.sh` when `FW_VER=1.4.49`) verifies stock bytes, then
writes ARM NOP (`00 00 a0 e1`). Refuses on mismatch.

## Verification
- Pristine stock: both sites disassemble to `nop`; re-run refuses.
- Behavior: exhaust fan stays off during prints unless explicitly controlled.
