### Api control patch

Patched using disassembly and the existing 1.1.40 patch behavior. The 1.4.46 target is `sub_370738` at offset `0x00370738`. For easier searching, search for the string `device is busy,can't set status\n`.

In 1.4.46 the earlier 1.1.40 two-condition busy check has been reduced to a single busy-state branch. Patch the branch at `0x003707f8` from `bne 0x00370a64` to `nop` (`mov r0, r0`). This prevents the API status update path from jumping to the busy error handler while printing and allows the normal status-setting code to continue.
