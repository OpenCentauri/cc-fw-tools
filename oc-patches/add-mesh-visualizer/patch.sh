#!/bin/bash

if [ $UID -ne 0 ]; then
  echo "Error: Please run as root."
  exit 1
fi

set -e

cp "$CURRENT_PATCH_PATH/mesh.html" "$SQUASHFS_ROOT/app/resources/www/mesh.html"