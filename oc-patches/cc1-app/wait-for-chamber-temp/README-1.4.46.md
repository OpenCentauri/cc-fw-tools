# TEMPERATURE_WAIT Box Sensor Patch

Adds chamber (`box`) temperature support to `TEMPERATURE_WAIT` for firmware 1.4.46 without changing stock heater behavior. **Status: disabled for 1.4.46** pending a safe trampoline rebuild; the current 1.4.46 trampoline can corrupt the `TEMPERATURE_WAIT` stack frame and crash during startup.

## How to use
```
M400
TEMPERATURE_WAIT SENSOR=box MINIMUM=XX MAXIMUM=YY
M400
```

## Technical

Patched original function: `sub_1779b0`

Addresses patched:
- `0x00177bc8` changes from `bl sub_ed718` to `b 0x00450100`
- New code range: `0x00450100`-`0x004501d7`

The injected code checks the original `SENSOR` string for `box`, requests `srv_state` through `sub_2b83c`, reads the shifted 1.4.46 chamber temperature field at status offset `0x48`, compares it against the `MINIMUM`/`MAXIMUM` values already parsed by `TEMPERATURE_WAIT`, sleeps with `usleep(10000)` while out of range, and returns through the stock epilogue at `0x00177dd8` when the wait is complete or the sensor is not `box`.

Compared with the 1.1.40 patch, the 1.4.46 stub allocates a larger scratch frame because `srv_state` now copies `0xd0` bytes instead of the older `0x58` byte state structure.
