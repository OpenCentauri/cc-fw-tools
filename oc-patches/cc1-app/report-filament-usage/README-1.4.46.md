# Filament Usage JSON Patch

This is the firmware 1.4.46 port of the PrintInfo filament usage patch. It adds the same two hex-keyed JSON fields as the 1.1.40 patch:

- cumulative extrusion from the stored E-position double
- current-cycle extrusion delta, computed as current total minus the previously stored total

## Technical

Patched original function: the PrintInfo JSON writer around `sub_36b980`.

Addresses patched:
- `0x0036bf38` replaces the stock `movt/vmov/vcvt` sequence after the `TotalLayer` key with `movw ip, #0x0a00; movt ip, #0x45; bx ip`
- New total key string: `0x00450920`
- New current delta key string: `0x00450980`
- New code range: `0x00450a00`-`0x00450ac3`
- Persistent `.bss` scratch doubles: `0x004b4788` and `0x004b4790`

The injected code first replays the three instructions clobbered by the hook and calls the stock JSON double helper at `0x002c9020` so `TotalLayer` is still emitted. It then loads `data_4b1034`, dereferences the printer object pointer at `+0xf8`, reads the double at `+0x1c0`, stores the current total at `0x004b4788`, computes the delta against the previous total, stores that delta at `0x004b4790`, and emits both values through the same JSON helper.

Compared with 1.1.40:
- the hook moved from `0x002deb18` to `0x0036bf38`
- the JSON helper moved from `0x00268720` to `0x002c9020`
- the printer global moved from `0x003e54d4` to `0x004b1034`
- the code cave moved from `0x00392680` to `0x00450a00`
- the BSS scratch moved from `0x003e8740`/`0x003e8748` to `0x004b4788`/`0x004b4790`

The generated patch file is `report_filament_usage_patch-1.4.46.bsdiff`.
