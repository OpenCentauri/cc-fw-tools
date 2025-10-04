#!/bin/bash -x
#
# Script to run through all the firmware extract, patch and build steps!
#

project_root="$PWD"

# Source the utils.sh file
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"

# files needed
FILES="sw-description sw-description.sig boot-resource uboot boot0 kernel rootfs dsp0 cpio_item_md5"

# check the required tools
check_tools "grep md5sum openssl wc awk sha256sum mksquashfs git git-lfs"

echo "Unpacking the firmware..."
sudo ./unpack.sh FW/FW-CentauriCarbon-v1.1.40-2025-08-15.bin
if [ $? -ne 0 ]; then
    echo "Error unpacking the firmware, aborting..."
    exit 1
fi
echo

echo "Patching the firmware..."
sudo ./patch.sh
if [ $? -ne 0 ]; then
    echo "Error patching the firmware, aborting..."
    exit 1
fi
echo

echo "Re-packing the firmware into update/update.swu..."
sudo ./pack.sh
if [ $? -ne 0 ]; then
    echo "Error re-packing the firmware, aborting..."
    exit 1
fi
echo
