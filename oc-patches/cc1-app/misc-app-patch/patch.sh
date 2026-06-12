#!/bin/bash

if [ $UID -ne 0 ]; then
  echo "Error: Please run as root."
  exit 1
fi

cd "$SQUASHFS_ROOT"

echo Install OpenCentauri firmware public key
cp ../../RESOURCES/KEYS/swupdate_public.pem ./etc/swupdate_public.pem
cp ../../RESOURCES/KEYS/swupdate_public.pem ./etc/swupdate_public_oc.pem
cp ../../RESOURCES/KEYS/swupdate_public_cc.pem ./etc/swupdate_public_cc.pem

echo Applying UTF-8 fix to prevent webui from breaking
echo "/sbin/utf8-fix /user-resource/file_info/file_info.txt" >> "./etc/rc.local"

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

echo Block Elegoo automated FW updates from Chitui via hosts file entry
sed -re '1a # Block automatic software updates from Elegoo\n127.0.0.1 mms.chituiot.com' -i ./etc/hosts

echo "Install 'noapp' script in /usr/sbin"
cat "$CURRENT_PATCH_PATH/noapp" > ./usr/sbin/noapp
chmod 755 ./usr/sbin/noapp

echo "Install update-printer-cfg.py in /app"
cat "$CURRENT_PATCH_PATH/update-printer-cfg.py" > ./app/update-printer-cfg.py
chmod 755 ./app/update-printer-cfg.py

cat "$CURRENT_PATCH_PATH/rc.local" >> ./etc/rc.local