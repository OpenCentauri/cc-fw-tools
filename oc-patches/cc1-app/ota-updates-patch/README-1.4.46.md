# OTA updates for OpenCentauri on 1.4.46

This patch bundle patches 3 functions and 1 string in the 1.4.46 `app` binary:

- Patch `hl_net_wan_is_connected` at `0x002f8930` to branch directly to
  `hl_net_lan_is_connected` at `0x002f88ec`.

- Patch `hl_netif_wan_is_connected` at `0x002f9af8` to branch directly to
  `hl_netif_lan_is_connected` at `0x002f9ac0`.

- Patch `is_ota_version_greater` in the OTA code at `0x002c275c`. The patched
  body checks whether `ota_ctx.info[OTA_FIREMARE_CH_SYS].version` at `0x004aed3d`
  is non-empty instead of comparing the fetched OTA version against the stock
  firmware version.

- Patch string `"https://mms.chituiot.com/"` at `0x0044738c` to
  `"https://u.opencentauri.cc/"`.

The 1.4.46 port mirrors the 1.1.40 patch behavior, with the same two WAN-to-LAN
redirects, the same non-empty-version OTA update check, and the same OpenCentauri
update endpoint replacement.
