#!/bin/bash

if [ $UID -ne 0 ]; then
  echo "Error: Please run as root."
  exit 1
fi

project_root="$REPOSITORY_ROOT"
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"

check_tools "grep md5sum openssl wc awk sha256sum mksquashfs git git-lfs"

echo Go into the squashfs-root dir for the rest of the steps!
cd "$SQUASHFS_ROOT"

set -e

: "${KIP_BOOTSTRAP_URL:?KIP_BOOTSTRAP_URL must be set in $PATCHES_ROOT/patch_config}"
: "${KIP_BOOTSTRAP_PATH:?KIP_BOOTSTRAP_PATH must be set in $PATCHES_ROOT/patch_config}"
: "${KIP_BOOTSTRAP_SHA256:?KIP_BOOTSTRAP_SHA256 must be set in $PATCHES_ROOT/patch_config}"

#echo Copy over the OpenCentauri bootstrap tarball to /app
#cp "$CURRENT_PATCH_PATH/OpenCentauri-bootstrap.tar.gz" ./app
#chmod 644 ./app/OpenCentauri-bootstrap.tar.gz
echo Copy over the Kipware bootstrap tarball to /app
wget "$KIP_BOOTSTRAP_URL" -O "$KIP_BOOTSTRAP_PATH"
chmod 644 "$KIP_BOOTSTRAP_PATH"

echo Check hash on Kipware bootstrap
SHA_SUM="$(sha256sum "$KIP_BOOTSTRAP_PATH" | awk '{print $1}')"
if [[ ! "$SHA_SUM" = "$KIP_BOOTSTRAP_SHA256" ]]; then
  printf "SHA256 hash of %s (%s) does not match expected %s, aborting...\n" "$KIP_BOOTSTRAP_PATH" "$SHA_SUM" "$KIP_BOOTSTRAP_SHA256"
  exit 1
fi

echo 'Add symlink for /lib/modules/ for new kernel ver 5.4.61-${kmod} (harmless for earlier revs)'
cd ./lib/modules
if [ "$FW_VER" = "1.1.40" ]; then
  kmod=ab1175
elif [ "$FW_VER" = "1.4.44" ]; then
  kmod=ab1434
elif [ "$FW_VER" = "1.4.46" ]; then
  kmod=ab1444
fi
echo 'Add symlink for /lib/modules/ for new kernel ver 5.4.61-${kmod} (harmless for earlier revs)'
[[ ! -z "$kmod" ]] && ln -sf 5.4.61 5.4.61-$kmod
cd -

echo $VERSION

echo "Install Ethernet kmod(s)"
if [[ ! -z "$kmod" ]]; then
  cp "$CURRENT_PATCH_PATH/kmod-$kmod/r8152.ko" "$SQUASHFS_ROOT/lib/modules/5.4.61/"
  cp "$CURRENT_PATCH_PATH/kmod-$kmod/ax88179_178a.ko" "$SQUASHFS_ROOT/lib/modules/5.4.61/"
fi

echo Installing automatic wifi scripts/automation to run on boot
# Install oc-startwifi.sh script to /app:
cat "$CURRENT_PATCH_PATH/oc-startwifi.sh" > ./app/oc-startwifi.sh
chmod 755 ./app/oc-startwifi.sh

echo Installing COSMOS-like flash script
cat "$CURRENT_PATCH_PATH/flash" > ./usr/sbin/flash
chmod 755 ./usr/sbin/flash
cat "$CURRENT_PATCH_PATH/switch-to-cosmos" > ./usr/sbin/switch-to-cosmos
chmod 755 ./usr/sbin/switch-to-cosmos

# Install flash-artifact and update-patched utilities
cat "$CURRENT_PATCH_PATH/flash-artifact" > ./usr/sbin/flash-artifact
chmod 755 ./usr/sbin/flash-artifact
cat "$CURRENT_PATCH_PATH/update-patched" > ./usr/sbin/update-patched
chmod 755 ./usr/sbin/update-patched

echo Installing automatic NTP date/time sync to run on boot
cat "$CURRENT_PATCH_PATH/ntpdate" > ./usr/sbin/ntpdate
chmod 755 ./usr/sbin/ntpdate

# Install 'mount_usb' script in /usr/sbin
cat "$CURRENT_PATCH_PATH/mount_usb" > ./usr/sbin/mount_usb
chmod 755 ./usr/sbin/mount_usb

# Install 'mount_usb_daemon' script in /usr/sbin
cat "$CURRENT_PATCH_PATH/mount_usb_daemon" > ./usr/sbin/mount_usb_daemon
chmod 755 ./usr/sbin/mount_usb_daemon

cp "$CURRENT_PATCH_PATH/oc-emergency" ./etc/init.d/oc-emergency
sed -re "s|%OC_NTP_SERVER%|$OC_NTP_SERVER|g" -i ./etc/init.d/oc-emergency
chmod 755 ./etc/init.d/oc-emergency
ln -s ../init.d/oc-emergency ./etc/rc.d/S83oc-emergency
chmod 755 ./etc/rc.d/S83oc-emergency

cp "$CURRENT_PATCH_PATH/oc-bootstrap" ./etc/init.d/oc-bootstrap
chmod 755 ./etc/init.d/oc-bootstrap
ln -s ../init.d/oc-bootstrap ./etc/rc.d/S85oc-bootstrap
chmod 755 ./etc/rc.d/S85oc-bootstrap
