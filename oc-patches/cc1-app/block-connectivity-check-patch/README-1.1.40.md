### Connectivity check block binary patch

Jumps past these 2 lines out ([source referece](https://github.com/elegooofficial/CentauriCarbon/blob/20a2d9b40e0005746c300766e0b526934997805e/firmware/hl/devices/hl_net.c#L218)) using simple nop's and b statements.

```c
    HL_ASSERT(hl_tpool_create_thread(&net_wan_connect_detction_thread, net_wan_connect_detection_routine, NULL, 0, 0, 0, 0) == 0);
    HL_ASSERT(hl_tpool_wait_started(net_wan_connect_detction_thread, 0) == 1);
```
