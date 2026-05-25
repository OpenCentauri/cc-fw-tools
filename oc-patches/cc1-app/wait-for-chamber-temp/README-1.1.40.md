# TEMPERATURE_WAIT Box Sensor Patch

Adds chamber ('box') temperature support to TEMPERATURE_WAIT without changing stock heater behavior. The patch diverts only if the SENSOR provided is not found in *Heaters

## What This Enables
TEMPERATURE_WAIT SENSOR=box MINIMUM=X now waits until chamber temperature ≥ MAXIUMUM, chamber temperature ≤ MINIMUM, and continues.
Printer/screen/webUI remains responsive during wait.  Note that fan speeds/heater temps cannot be changed during this time.
Note - Add M400 before and after the command to make sure all instructions process appropriately

## How to use
```
M400
TEMPERATURE_WAIT SENSOR=box MINIMUM=XX MAXIMUM=YY
M400
```
New function is hard-coded to chamber temp for now.  Both MINIMUM and MAXIMUM must be provided, however only MINIMUM is assessed  
-example - 
```
M400
TEMPERATURE_WAIT SENSOR=box MINIMUM=45 MAXIMUM=60
M400
```
--- This will wait (indefinitely) for the chamber temp to reach at least 45 and no more than 60 before proceeding to the next line of gcode

## TODO:
- [x] Enable MAXIMUM evaluation as well as minimum  
- [x] Ensure arg1 is 'box', return if not  
- [ ] Emit error to log for the above  
- [ ] Patch stock (heater) branch of TEMPERATURE_WAIT to prevent soft-locking while waiting

## Technical:

Addresses Patched  
0x00165A30 – becomes a jump to new code at 0x00391EC0  
New code range: 0x00391EC0–0x00391F94

Patched Original Function Bytes  
```
0x00165A30  EB FD F2 74 => 22 B1 08 EA

bl sub_e2408  →  b 0x00391EC0
```

Used:  
simple_bus_request to get chamber temp  
usleep to wait without freezing  
existing registers and calls from TEMPERATURE_WAIT