# FIX_END_PRINT_HANG binary patch for CC1 app 1.4.46

## Summary

`FIX_END_PRINT_HANG` sends:

```gcode
M117 OpenCentauri Print Complete
```

when the stock app observes the transition from printing to not-printing in
`app_top.cpp` (`sub_35cf58`). This is intended to work around the stock firmware
end-print hang by forcing the normal M117/display-status path to run at
completion.

## Hook site

- Function: `sub_35cf58` (`app/e100/app_top.cpp` periodic handler)
- End-print log: `0x0035db98`, `"end printing...\n"`
- Hook: `0x0035dba4`
- Original instruction: `strb r5, [r4, #0x62c]`
- Patched instruction: `b 0x00450b00`
- Resume: `0x0035dbac`

The stock second store at `0x0035dba8` remains in the file but is skipped by the
branch. The trampoline replays both stock stores before queueing the M117.

## Code/data cave

- Trampoline: `0x00450b00`-`0x00450b7f`
- Command string: `0x00450c00`-`0x00450c3f`
- Existing cave top before this patch: `0x00450ac3`

## Why this does not collide

Existing 1.4.46 caves:

- `fix-noncanvas-load`: `0x00450100`-`0x00450147`
- `wait-for-chamber-temp`: `0x00450200`-`0x004502d7`
- `report-filament-usage`: code `0x00450a00`-`0x00450ac3`, strings `0x00450920` and `0x00450980`

This patch starts at `0x00450b00`, after all existing caves.

`disable-exhaust-fan-patch` touches the same app-top function but only at
`0x0035d508` and `0x0035d5d4`; this patch hooks `0x0035dba4`, so there is no
byte overlap.

## G-code queue helper

The trampoline calls the existing stock helper:

```text
sub_50b88(data_4b1034[0x39], "M117 OpenCentauri Print Complete", 0)
```

`sub_50b88` is already used by stock code to enqueue formatted G-code such as
`M104 S0`, `M140 S0`, `M107`, `M211 S0/S1`, and `G29.1 P0/P1`.

## Verification

Generated against the pre-`FIX_END_PRINT_HANG` intermediate app in full
`patch_planner.py` order. `patch.toml` marks the app-binary patches in that
baseline as `requires` so the build fails early if the chain is changed without
regenerating this bsdiff:

```text
prepatch app sha256: 80e636221be0843793e2283d364b68dea7ced9ae744bf9c09798d0970d5e9cf3
patched app sha256:  6d24924bff23083836678a4cda6446c7e6859ec9b9a61fccdc332f611b013b05
bsdiff sha256:       f62e7ca5c7f6ab5c38c67f3dbb1c48e7bae2acfba74a56c5518efad7ed9eac9e
```

## Runtime validation

1. Boot patched 1.4.46 firmware.
2. Start a short print.
3. Let it finish normally.
4. Confirm logs include stock `end printing...` once.
5. Confirm the queued G-code includes / causes `M117 OpenCentauri Print Complete` once.
6. Confirm the touchscreen/UI does not remain stuck in the stock end-print hang state.
7. Confirm cancel/pause/resume paths do not emit an unwanted false completion message.
