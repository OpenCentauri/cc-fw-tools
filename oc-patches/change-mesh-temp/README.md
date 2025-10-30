# Bed Mesh Temp Change Patch

## Summary
Binary patching of 0x36d7bc performed to update the bed mesh preheat command from "M109 S60" to "M109 SXX" using the BED_MESH_TEMP value (35–99°C)

## Summary
Allow user to set default meshing temp between 35C and 99C (hardcoded val is 60C)

---

## Verification
- [x] Confirm patched binary boots normally  
- [x] Confirm mesh happens at XXC
- [x] Verify mesh saves
