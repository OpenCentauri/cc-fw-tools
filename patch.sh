#!/bin/bash
#
# Script to apply the standard patchset for OpenCentauri Firmware Build
#
DEBUG_PATCH=0

if [ $UID -ne 0 ]; then
  echo "Error: Please run as root."
  exit 1
fi

project_root="$PWD"

# Source the utils.sh file
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"

# files needed
FILES="sw-description sw-description.sig boot-resource uboot boot0 kernel rootfs dsp0 cpio_item_md5"

# check the required tools
check_tools "grep md5sum openssl wc awk sha256sum mksquashfs git git-lfs"

# Source the ./patch_config config settings!
. $(dirname $0)/patch_config

echo "Go into the squashfs-root dir for the rest of the steps!"
cd ./unpacked/squashfs-root

if [ $DEBUG_PATCH = 1 ]; then
set -x
fi

echo "Check MD5sum on OpenCentauri bootstrap"
if [[ ! $(md5sum "$OC_BOOTSTRAP" | awk '{print $1}') = "$OC_BOOTSTRAP_MD5" ]]; then
  printf "MD5 hash of %s does not match expected %s, aborting...\n" "$OC_BOOTSTRAP" "$OC_BOOTSTRAP_MD5"
  exit 1
fi

echo "Copy over the OpenCentauri bootstrap tarball to /app"
cp ../../RESOURCES/OpenCentauri/OpenCentauri-bootstrap.tar.gz ./app
chmod 644 ./app/OpenCentauri-bootstrap.tar.gz

echo "Install OpenCentauri firmware public key"
cat ../../RESOURCES/KEYS/swupdate_public.pem > ./etc/swupdate_public.pem

echo "Install OpenCentauri banner file"
cat ../../RESOURCES/OpenCentauri/banner > ./etc/banner

echo "Configure bind-shell for recovery purposes on 4567/tcp"
cat ../../RESOURCES/OpenCentauri/bind-shell > ./app/bind-shell
chmod 755 ./app/bind-shell
cat ../../RESOURCES/OpenCentauri/12-shell > ./etc/hotplug.d/block/12-shell
chmod 644 ./etc/hotplug.d/block/12-shell

echo "Block Elegoo automated FW updates from Chitui via hosts file entry"
sed -re '1a # Block automatic software updates from Elegoo\n127.0.0.1 mms.chituiot.com' -i ./etc/hosts

echo "Set root password to 'OpenCentauri'"
sed -re 's|^root:[^:]+:(.*)$|root:$1$rjtTIZX8$BmFRX/0pY6iP8VemQeOhN/:\1|' -i ./etc/shadow

echo "Add mlocate group"
sed -re 's|^(network.+)$|\1\nmlocate:x:102:|' -i ./etc/group

echo "Fix fgrep error on login in /etc/profile"
sed -re 's|fgrep|grep -F|' -i ./etc/profile

echo "Create sshd privilege separation user"
echo 'sshd:x:22:65534:OpenSSH Server:/opt/var/empty:/dev/null' >> ./etc/passwd

echo "Set hostname to OpenCentauri"
sed -re 's|TinaLinux|OpenCentauri|' -i ./etc/config/system

echo 'Update web interface JavaScript and overlay image(s)'
cat ../../RESOURCES/OpenCentauri/opencentauri-logo-small.png > ./app/www/assets/images/network/logo.png
# Need to re-size logo width from 160px to 300px so it's not to small, since wider!
sed -re 's|(logo-img\[.+\])\{width:160px\}|\1{width:300px}|' -i ./app/www/*.js

echo "Add OpenCentauri initialization to /etc/rc.local"
# Just copy in the modified /etc/rc.local, need to make this better...
cat ../../RESOURCES/OpenCentauri/rc.local > ./etc/rc.local
# Do edits to this file from ./patch_config
sed -re "s|%OC_APP_BOOT_DELAY%|$OC_APP_BOOT_DELAY|g" -i ./etc/rc.local
sed -re "s|%OC_APP_GADGET%|$OC_APP_GADGET|g" -i ./etc/rc.local

echo "Installing automatic wifi scripts/automation to run on boot"
# Install oc-startwifi.sh script to /app:
cat ../../RESOURCES/OpenCentauri/oc-startwifi.sh > ./app/oc-startwifi.sh
chmod 755 ./app/oc-startwifi.sh
# Install Sims awesome wifi ssid extractor to /app:
cat ../../RESOURCES/OpenCentauri/wifi-network-config-tool > ./app/wifi-network-config-tool
chmod 755 ./app/wifi-network-config-tool

# Install 'noapp' script in /usr/sbin
cat ../../RESOURCES/OpenCentauri/noapp > ./usr/sbin/noapp
chmod 755 ./usr/sbin/noapp
# Install 'mount_usb' script in /usr/sbin
cat ../../RESOURCES/OpenCentauri/mount_usb > ./usr/sbin/mount_usb
chmod 755 ./usr/sbin/mount_usb
# Install 'mount_usb_daemon' script in /usr/sbin
cat ../../RESOURCES/OpenCentauri/mount_usb_daemon > ./usr/sbin/mount_usb_daemon
chmod 755 ./usr/sbin/mount_usb_daemon

if [ $INCLUDE_CUSTOM_SPLASH = 1 ]; then
cp ../../RESOURCES/OpenCentauri/boot-resource ../boot-resource
echo "Custom Boot-resource copied in!"
fi

# TODO: Fix swupdate_cmd.sh -i /mnt/exUDISK/update/update.swu -e stable,now_A_next_B -k /etc/swupdate_public.pem
# Write log to /mnt/exUDISK/ instead of /mnt/UDISK

cd -
