# Allow Uploads During Printing (CC1 1.4.49)

## Purpose
Stock 1.4.49 rejects file uploads while a print is running. This patch NOPs the
two guard branches that divert to the `device is busy,can't upload` error flow
in the SDCP v3 HTTP handler (`fcn.0036a5c8`, VA `0x36a5c8`–`0x36b52b`), matching
the 1.1.40 patch intent.

## Sites (1.4.49)

| Guard | Site VA | File offset | Stock bytes (LE) | Stock instr | Patched |
|---|---|---|---|---|---|
| `sub_36c8cc(1)==1` → busy | `0x0036acb4` | `0x0035acb4` | `6401000a` | `beq 0x36b24c` | `nop` |
| `sub_13d53c(obj)!=0` → busy | `0x0036acdc` | `0x0035acdc` | `5a01001a` | `bne 0x36b24c` | `nop` |

Error flow target `0x36b24c` (log code `0x2ee`, string `device is busy,can't
upload` @ VA `0x4590a0`) becomes unreachable from this handler.

## Mechanism
`patch.py` (invoked via `patch.sh` when `FW_VER=1.4.49`) verifies the expected
stock bytes at both sites before writing anything, then writes ARM NOP
(`00 00 a0 e1`). Refuses on any mismatch (wrong baseline or already patched).

## Busy-flag note (1.4.49)
`sub_13d53c` (`ldrb r0,[r0,#0x40]`) is the canonical busy-flag reader with ~50
call sites — it is NOT hooked globally; only this handler's branches are NOPed.
The state dispatcher `sub_36c8cc(1)` reads bit 1 of byte `+0x13` of the global
state struct at `0x4b1c88`.

## Verification
- Apply to pristine stock `app-1.4.49`: both sites disassemble to `nop`; re-run
  refuses with "refusing to patch".
- Behavior: uploads succeed mid-print (web UI / slicer upload while printing).
  If uploads still fail on-hardware, note: the NOPs leave the busy result in
  fallthrough registers (`str r3,[sp,#0x34]` downstream) — a *later* check
  re-reading it would mean the patch is ineffective, not corrupting (same
  shape as shipped 1.1.40/1.4.46, so unlikely).
