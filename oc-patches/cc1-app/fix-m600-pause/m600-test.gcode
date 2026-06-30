; Minimal M600 reproduction test for CC1 1.4.46
; This gcode triggers an M600 at a known position with a tool temp of 220 °C.
; On the broken 1.4.46 firmware the printer unloads, then the hotend falls to
; 0 °C and the UI hangs on "load filament".
; With FIX_M600_PAUSE applied the hotend should remain at 200 °C and the load
; UI should allow filament insertion.

M104 S220
M109 S220
G28
G1 X100 Y100 F6000
M600
G1 X150 Y150 F6000
M104 S0
M140 S0
M84
