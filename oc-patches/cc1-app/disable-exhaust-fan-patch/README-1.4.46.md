# Disable Exhaust Fan Patch

This is the firmware 1.4.46 port of the patch that stops the app from automatically driving the chamber exhaust fan during a print.

## Technical

Patched using the 1.1.40 control flow as a reference. In 1.1.40, the patch NOPed the final `if (result)` branch in the app top periodic handler so it skipped both `sub_2c60ac()` and the exhaust-fan update call `sub_2c5ed0()`.

In 1.4.46, the equivalent periodic handler is `sub_35cf58`. The exhaust fan update code is still easy to locate from the separate function containing the string `real_fan_speed = %d`; that helper moved from `sub_2c5ed0` to `sub_34140c`.

Addresses patched:
- `0x0035d508`: changed `bne 0x0035d5d8` to `nop`, bypassing the fan block on the main post-print-state path
- `0x0035d5d4`: changed `beq 0x0035d50c` to unconditional `b 0x0035d50c`, bypassing the same fan block on the alternate already-printing path

The shared fan block starts at `0x0035d5d8`; it checks `sub_341720()` and then calls `sub_34140c()` when the exhaust fan should be updated. Patching both incoming edges preserves the 1.1.40 behavior of skipping the whole block rather than only NOPing the final call.

The generated patch file is `exhaust-fan-patch-1.4.46.bsdiff`.
