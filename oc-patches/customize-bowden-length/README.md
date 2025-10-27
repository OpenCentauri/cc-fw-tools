# Bowden Tube Length Patch

## Summary
Binary patching of 0x2c81f8 performed to update the bowden tube length from 700mm to any desired value

**Current bsdiff sets this to 10mm for testing only - do not use!**

---

## Verification
- [x] Confirm patched binary boots normally  
- [x] Confirm print pauses correctly after filament runout sensor trips  
- [x] Verify pause timing is nearly immediate after trip event  

---

## TODO
- [x] Write parameterized script to accept user-entered Bowden length values  
~~- [x] Generate and apply `bsdiff` at runtime~~ 
