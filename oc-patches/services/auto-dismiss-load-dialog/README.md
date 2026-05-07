# auto-dismiss-load-dialog

Auto-dismisses the "Load filament complete" modal that appears on the
Centauri Carbon's touchscreen at the end of a filament-load cycle. The
print queue is blocked while the dialog is up, so without this you have
to walk to the printer, tap OK, and walk back to your computer to start
the next print.

The unload-complete dialog **does not** appear (no auto-dismiss needed
there); only loads produce a blocking confirmation.

## How it works

Three pieces, all installed under `/opt`:

| File | Role |
|---|---|
| `/opt/sbin/synth-tap` | bash + `xxd` script that synthesises one touchscreen tap by writing `input_event` structs to `/dev/input/event1` |
| `/opt/sbin/auto-dismiss-daemon` | `tail -F`s `/board-resource/log1`, watches for the load-complete signal, then calls `synth-tap` |
| `/opt/etc/init.d/S99auto-dismiss` | entware service script (start/stop/restart/status), auto-started on boot via `rc.unslung` |

Detection signal — three log-line states from `/board-resource/log1`:

```
[app][...]:feed state change : 0 -> 1     ← load OR unload starts; reset
[gcode][...]:single_command<M729>         ← cycle is a load (load-only gcode)
[app][...]:feed state change : 1 -> 0     ← cycle ends; if is_load, tap
```

`M729` was identified as the cleanest load-only discriminator by
diffing the load and unload gcode sequences. Unloads run
`G1 E-60 F240` + `SET_MIN_EXTRUDE_TEMP S0/RESET`; loads run
`G1 E120 F240` + `M729`. Picking `M729` means we don't have to
interpret signed extrude values or filament-specific heater targets.

Tap synthesis matches the gt9xxnew_ts driver's recorded sequence
(captured from a real user tap on V0.3.0-o):

```
EV_KEY  BTN_TOUCH=1
EV_ABS  ABS_MT_POSITION_X = 289      ← OK button on the load-complete dialog
EV_ABS  ABS_MT_POSITION_Y = 182
EV_ABS  ABS_MT_TOUCH_MAJOR = 20
EV_ABS  ABS_MT_WIDTH_MAJOR = 20
EV_ABS  ABS_MT_TRACKING_ID = 0
EV_SYN  SYN_MT_REPORT
EV_SYN  SYN_REPORT
sleep 150 ms
EV_KEY  BTN_TOUCH=0
EV_SYN  SYN_REPORT
```

## Configuration

The daemon reads three env vars (with defaults):

| Var | Default | Notes |
|---|---|---|
| `LOG` | `/board-resource/log1` | path to `app`'s log file |
| `TAP_X` | `289` | OK-button X (gt9xxnew coordinate space) |
| `TAP_Y` | `182` | OK-button Y |
| `SETTLE_S` | `0.7` | settle delay between detection and tap |

Override by editing `/opt/etc/init.d/S99auto-dismiss` to set them
before starting the daemon.

## Footprint

- ~6 KB on disk
- Runs one bash process tailing one log file; idle CPU is rounding
  error
- Only writes to `/dev/input/event1` when `M729` + `feed state
  change : 1 -> 0` are observed in sequence

## Tested on

Firmware V0.3.0-o (OpenCentauri based on stock 1.1.40), Centauri
Carbon (CC1).
