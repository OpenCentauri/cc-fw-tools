# OTA updates for OpenCentauri on 1.4.49

This patch bundle patches 3 functions and 1 string in the 1.4.49 `app` binary:

- Patch `hl_net_wan_is_connected` at `0x002f9490` to branch directly to
  `hl_net_lan_is_connected` at `0x002f944c`.

- Patch `hl_netif_wan_is_connected` at `0x002fa658` to branch directly to
  `hl_netif_lan_is_connected` at `0x002fa620`.

- Patch `is_ota_version_greater` in the OTA code at `0x002c32cc`. The patched
  body checks whether the system OTA version is non-empty instead of comparing
  the fetched OTA version against the stock firmware version.

- Patch string `"https://mms.chituiot.com/"` at `0x004487a4` to
  `"https://u.opencentauri.cc/"`.

The 1.4.49 port mirrors the existing 1.4.46 patch behavior while using the
corresponding function and string locations in the 1.4.49 binary.
