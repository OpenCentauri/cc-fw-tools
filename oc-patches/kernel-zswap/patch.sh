#!/bin/bash

set -e

cd "$SQUASHFS_ROOT"

# Copy files
mv ../kernel ../kernel-stock
cp -f "$CURRENT_PATCH_PATH/kernel" ../
cp "$CURRENT_PATCH_PATH/oc-zram-swap.sh" ./app

# Make sure we can run them
chmod a+x ./app/oc-zram-swap.sh

# Set up hook for ZRAM and eMMC swap
cat "$CURRENT_PATCH_PATH/rc.local" >> ./etc/rc.local
sed -re "s|%OC_ZRAM_SWAP%|$OC_ZRAM_SWAP|g" -i ./etc/rc.local
sed -re "s|%OC_EMMC_SWAP%|$OC_EMMC_SWAP|g" -i ./etc/rc.local
