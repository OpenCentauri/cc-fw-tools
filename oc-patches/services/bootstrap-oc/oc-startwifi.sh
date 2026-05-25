#!/usr/bin/env bash

wlan_conf="/board-resource/wlan_entery"
wlan_conf_str="/tmp/wlan_entery_str"
#strings "$wlan_conf" > "$wlan_conf_str"
# Run Sims' awesome wifi network config extractor!
wifi-network-config-tool /board-resource/wlan_entery extract | strings > "$wlan_conf_str"

echo "Cleanup old wlan stuff..."
kill $(cat /tmp/wlan0_udhcpc.pid) &>/dev/null
kill $(pgrep wpa_supplicant) &>/dev/null
sleep 1

echo "Bootstrapping wlan0..."
modprobe aic_load_fw
modprobe aic8800_fdrv
modprobe 8821cu
modprobe 8723du
sleep 2
wpa_supplicant -D nl80211,wext -C /var/run/wpa_supplicant -B -i wlan0

num_wlan=$(cat "$wlan_conf_str" | wc -l)
num_wlan=$((num_wlan / 2))
echo "Found networks: $num_wlan"

echo "Removing all configured networks..."
wpa_cli list_networks 2>&1 | sed -nr -e '3,$p' | sed -re 's|^([0-9]+).*$|\1|' | xargs -i -t wpa_cli remove_network {}

for ((i=1;i<=$num_wlan;i+=2)); do
  ssid_line=$i
  psk_line=$((ssid_line + 1))
  ssid="$(sed "${ssid_line}q;d" ${wlan_conf_str})"
  psk="$(sed "${psk_line}q;d" ${wlan_conf_str})"
  printf "[hl_wlan][%d][%d][%d]: append ssid %s psk %s\n" "$i" "$ssid_line" "$psk_line" "$ssid" "$psk"
  net_num=$(wpa_cli add_network | tail -1)

  # For some reason need to do all of these in a batch or it fails one-at-a-time from the CLI
  wpa_cli <<EOF
set_network $net_num ssid "$ssid"
set_network $net_num psk "$psk"
enable $net_num
quit
EOF
done
# Force a reconnect now that all networks are set-up!
wpa_cli reconnect
sleep 2

# Start DHCP service
#udhcpc -i wlan0 -b -p /tmp/wlan0_udhcpc.pid -s /usr/share/udhcpc/default.script -x hostname:Centauri-Carbon
udhcpc -i wlan0 -f -p /tmp/wlan0_udhcpc.pid \
  -s /usr/share/udhcpc/default.script \
  -x hostname:Centauri-Carbon \
  -A 5 -t 10 -T 3 &
