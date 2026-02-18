#!/opt/bin/bash

# Calculate memory availability
totalmem_kb=$(free | grep '^Mem' | awk '{print $2}')
mem_mb=$((totalmem_kb/1024))
zram_mb=$((mem_mb/2))  # Default to mem_mb / 2 for zram swap
swap_mb=$((mem_mb*2)) # Default to 2 x total_ram for eMMC swap
if [ $# -eq 2 ]; then
  swap_zram=$1
  swap_emmc=$2
else
  swap_zram=$zram_mb
  swap_emmc=$swap_mb
fi

swap_file=/opt/swapfile

# Disable existing zram / swap configuration
swapoff /dev/zram0
#rmmod zram
swapoff $swap_file

if [ $swap_zram -gt 0 ]; then
  # Set-up ZRAM swap sysctl settings (recommendations from https://wiki.archlinux.org/title/Zram)
  printf "Overriding sysctl settings for zram swap...\n"
  #sysctl -w vm.swappiness=180
  sysctl -w vm.swappiness=100
  sysctl -w vm.watermark_boost_factor=0
  sysctl -w vm.watermark_scale_factor=125
  sysctl -w vm.page-cluster=0
  sleep 1

  # Initialize ZRAM swap
  printf "Configuring for %dMB of zram swap space...\n" "$zram_mb"
  #modprobe zram
  echo 1 > /sys/block/zram0/reset
  echo $((swap_zram*1024*1024)) > /sys/block/zram0/disksize
  mkswap /dev/zram0
  swapon -p 100 /dev/zram0
fi

# Initialize eMMC swapfile (much lower priority)
if [ $swap_emmc -gt 0 ]; then
  printf "Configuring for %d MB of traditional swap space...\n" "$swap_emmc"
  if [ -f $swap_file ]; then
    curr_size=$(du -m $swap_file | awk '{print $1}')
  else
    curr_size=0
  fi
  if [[ $curr_size -ne $swap_emmc ]]; then
    dd if=/dev/zero of=$swap_file bs=1M count=$swap_emmc
  fi
  mkswap $swap_file
  swapon $swap_file
else
  # Clean-up eMMC swap file if not needed
  rm -f $swap_file
fi
swapon -s
