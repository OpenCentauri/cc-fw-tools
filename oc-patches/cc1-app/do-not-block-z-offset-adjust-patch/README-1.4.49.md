# Do Not Block Z-Offset Adjust (CC1 1.4.49)

## Purpose
Stock 1.4.49 blocks z-offset adjustment while a print is running:
`if (app_print_get_print_state() && (!app_print_get_print_busy() || !app_top_get_autoleveling_busy()))`
(Elegoo `app_setting.cpp`). This patch replaces the guard `bl` in both button
paths of `app_z_offset_callback` (`fcn.0034cb60`, VA `0x34cb60`–`0x34d44f`) with
an unconditional branch into the adjust body — identical relative deltas to the
1.1.40 patch.

## Sites (1.4.49)

| Path | Site VA | File offset | Stock bytes (LE) | Stock instr | Patched bytes (LE) | New instr |
|---|---|---|---|---|---|---|
| BTN_DOWN | `0x0034cc44` | `0x0033cc44` | `8bd7ffeb` | `bl 0x342a78` | `040000ea` | `b 0x34cc5c` |
| BTN_UP | `0x0034d20c` | `0x0033d20c` | `19d6ffeb` | `bl 0x342a78` | `460000ea` | `b 0x34d32c` |

`0x342a78` is the print_state getter (67 callers — not hooked globally).

## Mechanism
`patch.py` (via `patch.sh` when `FW_VER=1.4.49`) verifies stock bytes, then
writes the branch. Refuses on mismatch.

## Verification
- Pristine stock: sites disassemble to `b 0x34cc5c` / `b 0x34d32c`; re-run refuses.
- Behavior: z-offset buttons work during a print.
