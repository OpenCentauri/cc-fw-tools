# FIX_M600_PAUSE (1.4.46 only)

## Problem

On 1.4.46, `M600` filament-change pauses hang after the unload step. The UI
shows "load filament" indefinitely, and the hotend cools to 0 °C because the
temperature-setting step is never issued.

The 1.1.40 code path (`cc-firmware/core/klippy/extras/change_filament.cpp` and
`pause_resume.cpp`) ends `cmd_M600` by calling
`note_change_filament_completed()`, which signals the UI that the printer is
ready for the user to load filament. The UI then issues
`MOVE_TO_EXTRUDE TARGET_TEMP=...`, which sends `M104`/`M109` to reheat the
hotend before extruding the new filament.

In 1.4.46, `cmd_M600` (sub `0x1b81e4`) instead queues:

```text
PAUSE
CUT_OFF_FILAMENT
EXTRUDE_FILAMENT E=-60 F=240 FAN_ON=0 REPORT=0
```

and then dispatches the resume event (`sub_1c7908`). `CUT_OFF_FILAMENT` emits
`M104 S0`, turning the hotend off. The resume/change-filament event handler
and the UI load path never issue a temperature command, so the hotend falls to
0 °C and the load UI stays blocked waiting for heat.

## Fix

Hook the `bl sub_1c7908` at the end of the 1.4.46 M600 handler and inject a
temperature command before the event is dispatched:

```text
M104 S200
```

This keeps the hotend warm enough for manual filament insertion and lets the
subsequent UI `MOVE_TO_EXTRUDE` command raise the temperature to the final print
temperature and wait for it with `M109`.

The patch is compatible with both Canvas and non-Canvas configurations because
it only adds a temperature command and does not depend on any filament sensor
logic.

## Implementation

- **Hook:** `0x001b84c4` (`bl sub_1c7908`) → `b 0x00450d00`
- **Code cave:** `0x00450d00` — `0x00450d7f` (0x80 bytes reserved)
- **String cave:** `0x00450c40` — `0x00450c7f` (`M104 S200`)
- **Resume:** `0x001b84c8`

The trampoline preserves all registers, uses `sub_50b88` to enqueue the
temperature command, then tail-calls `sub_1c7908` so the original resume event
is still dispatched.

## Patch artifact

```text
fix-m600-pause-1.4.46.bsdiff
```

## Verification

After applying the patch, an `M600` in a print should:

1. Pause and move to the park position.
2. Unload the old filament.
3. Set the hotend to 200 °C.
4. Show the UI "load filament" prompt and allow the user to proceed.

A minimal reproduction gcode is included in `m600-test.gcode` (heats to 220 °C, homes, parks, issues `M600`, then parks again and shuts down).

## Notes

- `200` was chosen as a conservative loading temperature that works for PLA and
  PETG. The actual print temperature is restored by the `RESUME` command via
  `PauseResume::m_save_extruder_temp`.
- This patch does not modify the `CUT_OFF_FILAMENT` handler, so the normal
  load/unload UI flow still turns the hotend off as before.

## SHA-256

| File | SHA-256 |
|------|---------|
| pre-fix-m600-pause intermediate app (after fix-end-print-hang) | `7ecfb1d59873b376685078efcb7ea360b39fbf15cc737be2f06eb3d96ab75ff6` |
| post-fix-m600-pause app | `b64cec72a362136771748d43b02654d6b629b0813bb2fbe33f82e670b737f9ab` |
| bsdiff | `a453f07c4fc78f4f8c4cc0a84e4295fe0c5168f71fc1a6fc00cc7097b44dfeaf` |
