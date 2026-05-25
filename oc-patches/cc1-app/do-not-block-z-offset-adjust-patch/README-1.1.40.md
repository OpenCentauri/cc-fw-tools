### Always allow z offset adjust

Patched using binary ninja. Patches out the following line using b jumps ([source ref](https://github.com/elegooofficial/CentauriCarbon/blob/20a2d9b40e0005746c300766e0b526934997805e/firmware/app/e100/app_setting.cpp#L2388))

```c
if (app_print_get_print_state() && (!app_print_get_print_busy() || !app_top_get_autoleveling_busy()))
```