### Always allow z offset adjust for 1.4.46

Patched using the 1.1.40 bsdiff as the behavior reference. This patch removes the
print-state gate in the 1.4.46 `app_setting.cpp` Z-offset adjustment handler
`sub_34b7e0`.

The original source-level condition being bypassed is:

```c
if (app_print_get_print_state() && (!app_print_get_print_busy() || !app_top_get_autoleveling_busy()))
```

The 1.4.46 binary patch changes two branch sites:

- `0x0034b8c4`: replace `bl 0x00341700` with `b 0x0034b8dc`
- `0x0034be8c`: replace `bl 0x00341700` with `b 0x0034bfac`

These jumps skip the busy/printing checks for the down and up Z-offset adjustment
cases and enter the existing adjustment math directly.
