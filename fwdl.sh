#!/bin/bash

project_root="$PWD"

# Source the utils.sh file
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"

echo "Downloading Centauri Carbon Firmware version 1.1.25 from 2025-08-15..."
echo
# old url format up to 3.0.9
#url_zip="https://cdn.cloud-universe.anycubic.com/ota/${par_model}/AC104_${par_model}_1.1.0_${par_version}_update.zip"
url_bin="https://s3.devminer.xyz/archive/ELEGOO_Centauri_Update_1.1.40.bin"
file_bin="FW/FW-CentauriCarbon-v1.1.40-2025-08-15.bin"
curl "$url_bin" --output "$file_bin"
result=$(grep "<Code>NoSuchKey</Code>" "$file_bin")
file_size=$(wc -c "$file_bin" | awk '{print $1}')
echo
if [ -n "$result" ] || [ "$file_size" -le 1000000 ]; then
  rm -f "$file_bin"
  echo -e "${RED}ERROR: Cannot find an update for this model and version ${NC}"
  exit 3
else
  echo -e "${GREEN}Success! ${NC}"
fi
