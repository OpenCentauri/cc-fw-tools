# Connectivity Check Block Binary Patch

This is the firmware 1.4.46 port of the binary patch that prevents the WAN connectivity check thread from being started.

## Technical

The 1.1.40 patch skips the WAN detection thread creation block and NOPs the later `hl_tpool_wait_started(net_wan_connect_detction_thread, 0)` check. The LAN detection thread is still created and waited on.

In 1.4.46, the equivalent function is `sub_2f8150` in `hl_net.c`.

Addresses patched:
- `0x002f848c`: changed the start of the WAN thread creation setup to `b 0x002f84b4`, jumping directly to the LAN wait block
- `0x002f84cc`-`0x002f84e0`: replaced the six ARM instructions that wait on the WAN detection thread and branch to the WAN assertion failure path with NOPs

Compared with 1.1.40:
- the WAN creation skip moved from `0x002942b8` to `0x002f848c`
- the WAN wait NOP range moved from `0x002942f8`-`0x0029430c` to `0x002f84cc`-`0x002f84e0`
- the thread creation helper moved from `0x002a2ea4` to `0x003071ec`
- the thread wait helper moved from `0x002a3684` to `0x003079cc`

The generated patch file is `disable-connectivity-checks-1.4.46.bsdiff`.
