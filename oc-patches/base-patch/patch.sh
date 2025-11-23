#!/bin/bash
#
# Script to apply the standard patchset for OpenCentauri Firmware Build
#

if [ $UID -ne 0 ]; then
  echo "Error: Please run as root."
  exit 1
fi

project_root="$REPOSITORY_ROOT"

# Source the utils.sh file
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"

# files needed
FILES="sw-description sw-description.sig boot-resource uboot boot0 kernel rootfs dsp0 cpio_item_md5"

# check the required tools
check_tools "grep md5sum openssl wc awk sha256sum mksquashfs git git-lfs"

# Legacy AnyCubic option: Configure centauri carbon for serial UART and uboot shell
#OPTIONS_DIR="./RESOURCES/OPTIONS" ./RESOURCES/OPTIONS/uart/uart.sh . 2.3.9

echo Go into the squashfs-root dir for the rest of the steps!
cd "$SQUASHFS_ROOT"

set -x
set -e

echo Check MD5sum on OpenCentauri bootstrap
BOOTSTRAP_PATH="$CURRENT_PATCH_PATH/OpenCentauri-bootstrap.tar.gz"
MD5_SUM="$(md5sum "$BOOTSTRAP_PATH" | awk '{print $1}')"
if [[ ! "$MD5_SUM" = "$OC_BOOTSTRAP_MD5" ]]; then
  printf "MD5 hash of %s (%s) does not match expected %s, aborting...\n" "$BOOTSTRAP_PATH" "$MD5_SUM" "$OC_BOOTSTRAP_MD5"
  exit 1
fi

echo Copy over the OpenCentauri bootstrap tarball to /app
cp "$CURRENT_PATCH_PATH/OpenCentauri-bootstrap.tar.gz" ./app
chmod 644 ./app/OpenCentauri-bootstrap.tar.gz

echo Install OpenCentauri firmware public key
cp ../../RESOURCES/KEYS/swupdate_public.pem ./etc/swupdate_public.pem
cp ../../RESOURCES/KEYS/swupdate_public.pem ./etc/swupdate_public_oc.pem
cp ../../RESOURCES/KEYS/swupdate_public_cc.pem ./etc/swupdate_public_cc.pem

echo Install OpenCentauri banner file
cat "$CURRENT_PATCH_PATH/banner" > ./etc/banner

echo Configure bind-shell for recovery purposes on 4567/tcp
cat "$CURRENT_PATCH_PATH/bind-shell" > ./app/bind-shell
chmod 755 ./app/bind-shell
cat "$CURRENT_PATCH_PATH/12-shell" > ./etc/hotplug.d/block/12-shell
chmod 644 ./etc/hotplug.d/block/12-shell

echo Block Elegoo automated FW updates from Chitui via hosts file entry
sed -re '1a # Block automatic software updates from Elegoo\n127.0.0.1 mms.chituiot.com' -i ./etc/hosts

echo Set root password to 'OpenCentauri'
sed -re 's|^root:[^:]+:(.*)$|root:$1$rjtTIZX8$BmFRX/0pY6iP8VemQeOhN/:\1|' -i ./etc/shadow

echo Add mlocate group 
sed -re 's|^(network.+)$|\1\nmlocate:x:102:|' -i ./etc/group

echo Fix fgrep error on login in /etc/profile
sed -re 's|fgrep|grep -F|' -i ./etc/profile

echo Create sshd privilege separation user
echo 'sshd:x:22:65534:OpenSSH Server:/opt/var/empty:/dev/null' >> ./etc/passwd

echo Set hostname to OpenCentauri
sed -re 's|TinaLinux|OpenCentauri|' -i ./etc/config/system

echo 'Update web interface JavaScript and overlay image(s)'
cat "$CURRENT_PATCH_PATH/opencentauri-logo-small.png" > ./app/resources/www/assets/images/network/logo.png
# Need to re-size logo width from 160px to 300px so it's not to small, since wider!
sed -re 's|(logo-img\[.+\])\{width:160px\}|\1{width:240px}|' -i ./app/resources/www/*.js
# Adjust left padding for logo.
sed -re 's|padding:0 36px 0 145px|padding:0 36px 0 36px|' -i ./app/resources/www/*.js
# Remove store button
sed -re 's|(\.store-box\[_ngcontent-%COMP%\])\{cursor:pointer;margin-left:150px;display:flex;align-items:center;border-radius:4px;background:#000;font-family:Microsoft YaHei;padding:6px 10px;font-size:14px;font-weight:400;color:#fff;opacity:.8\}|\1{cursor:pointer;margin-left:150px;display:none;align-items:center;border-radius:4px;background:#000;font-family:Microsoft YaHei;padding:6px 10px;font-size:14px;font-weight:400;color:#fff;opacity:.8}|' -i ./app/resources/www/*.js
# Remove the top two corner radii  
sed 's/background:#101112!important;border-radius:4px 4px/background:#101112!important;border-radius:0px 0px/g' -i ./app/resources/www/*.js


echo Add OpenCentauri initialization to /etc/rc.local
cat "$CURRENT_PATCH_PATH/rc.local" >> ./etc/rc.local
# Do edits to this file from ./patch_config
sed -re "s|%OC_APP_BOOT_DELAY%|$OC_APP_BOOT_DELAY|g" -i ./etc/rc.local
sed -re "s|%OC_APP_GADGET%|$OC_APP_GADGET|g" -i ./etc/rc.local
sed -re "s|%OC_NTP_SERVER%|$OC_NTP_SERVER|g" -i ./etc/rc.local

echo 'Add symlink for /lib/modules/ for the 1.1.40 FW w/ new kernel ver 5.4.61-ab1175 (harmless for earlier revs)'
cd ./lib/modules
ln -sf 5.4.61 5.4.61-ab1175
cd -

echo Installing automatic wifi scripts/automation to run on boot
# Install oc-startwifi.sh script to /app:
cat "$CURRENT_PATCH_PATH/oc-startwifi.sh" > ./app/oc-startwifi.sh
chmod 755 ./app/oc-startwifi.sh
# Install Sims awesome wifi ssid extractor to /app:
cat "$CURRENT_PATCH_PATH/wifi-network-config-tool" > ./app/wifi-network-config-tool
chmod 755 ./app/wifi-network-config-tool

echo Installing automatic NTP date/time sync to run on boot
cat "$CURRENT_PATCH_PATH/ntpdate" > ./app/ntpdate
chmod 755 ./app/ntpdate

# Install 'noapp' script in /usr/sbin
cat "$CURRENT_PATCH_PATH/noapp" > ./usr/sbin/noapp
chmod 755 ./usr/sbin/noapp
# Install 'mount_usb' script in /usr/sbin
cat "$CURRENT_PATCH_PATH/mount_usb" > ./usr/sbin/mount_usb
chmod 755 ./usr/sbin/mount_usb
# Install 'mount_usb_daemon' script in /usr/sbin
cat "$CURRENT_PATCH_PATH/mount_usb_daemon" > ./usr/sbin/mount_usb_daemon
chmod 755 ./usr/sbin/mount_usb_daemon

echo Installing SSL certificates
cp "$CURRENT_PATCH_PATH/ca-bundle.crt" ./etc/ca-bundle.crt
sed -i '/^export PS1=/a export SSL_CERT_FILE="\/etc\/ca-bundle.crt"' ./etc/profile

echo Setup uninstaller
cp "$CURRENT_PATCH_PATH/uninstall.sh" ./app/uninstall.sh
chmod 755 ./app/uninstall.sh

# TODO: Fix swupdate_cmd.sh -i /mnt/exUDISK/update/update.swu -e stable,now_A_next_B -k /etc/swupdate_public.pem
# Write log to /mnt/exUDISK/ instead of /mnt/UDISK

cd -
