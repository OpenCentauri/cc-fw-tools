# Allow API During Printing (CC1 1.4.49)

## Purpose
Stock 1.4.49 rejects set-status API calls while a print is running
(`device is busy,can't set status`). This patch NOPs the single guard branch in
the set-status API handler (`fcn.00371b10`, VA `0x371b10`–`0x371f7b`), matching
the 1.1.40/1.4.46 patch intent.

## Site (1.4.49)

| Guard | Site VA | File offset | Stock bytes (LE) | Stock instr | Patched |
|---|---|---|---|---|---|
| busy-flag read != 0 → busy | `0x00371bd0` | `0x00361bd0` | `9900001a` | `bne 0x371e3c` | `nop` |

Context: `0x371bc4: ldr r0, [r3, #0x228]` (printer object field), `0x371bc8:
bl 0x13d53c` (busy-flag reader), `0x371bcc: subs r2, r0, #0`, then the patched
`bne` to the error flow at `0x371e3c` (log code `0xa71`).

The handler covers the SDCP set-status keys: TempTargetHotbed / TempTargetNozzle
/ TempTargetBox, ModelFan, ZOffset, LightStatus, PrintSpeedPct, etc.

## Mechanism
`patch.py` (via `patch.sh` when `FW_VER=1.4.49`) verifies stock bytes, then
writes ARM NOP (`00 00 a0 e1`). Refuses on mismatch.

## Verification
- Pristine stock: site disassembles to `nop` after patching; re-run refuses.
- Behavior: fan/temp/z-offset/light changes via API succeed mid-print.
