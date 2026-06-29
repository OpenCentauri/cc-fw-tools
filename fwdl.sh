#!/bin/bash

project_root="$PWD"

# Source the utils.sh file
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"

# --- Firmware Version Definitions ---
declare -A versions
versions["1.1.18"]="https://download.chitubox.com/chitusystems/chitusystems/public/printer/firmware/release/1/ca8e1d9a20974a5896f8f744e780a8a7/1/1.1.18/2025-03-31/74406d43dc314af7a174dba70487ac2b.bin"
versions["1.1.25"]="https://download.chitubox.com/chitusystems/chitusystems/public/printer/firmware/release/1/ca8e1d9a20974a5896f8f744e780a8a7/1/1.1.25/2025-05-09/219b4c9e67de4a1d99c7680164911ab5.bin"
versions["1.1.29"]="https://download.chitubox.com/chitusystems/chitusystems/public/printer/firmware/release/1/ca8e1d9a20974a5896f8f744e780a8a7/1/1.1.29/2025-06-18/810e5a7e9518452c9172e11a7d04a683.bin"
# Thanks Anna!
versions["1.1.40"]="https://s3.devminer.xyz/archive/ELEGOO_Centauri_Update_1.1.40.bin"
versions["1.1.42"]="https://download.chitubox.com/chitusystems/chitusystems/public/printer/firmware/release/1/ca8e1d9a20974a5896f8f744e780a8a7/1/1.1.42/2025-09-18/5de8bf345f044452a815dcf91241ddc0.bin"
# Thanks Anna!
versions["1.4.44"]="https://s3.devminer.xyz/archive/ELEGOO_Centauri_Update_1.4.44.bin"
versions["1.4.46"]="https://download.chitubox.com/chitusystems/chitusystems/public/printer/firmware/release/1/ca8e1d9a20974a5896f8f744e780a8a7/1/1.4.46/2026-05-08/104101205ee740a68a3bc049f0b03c70.bin"

declare -A dates
dates["1.1.18"]="2025-03-31"
dates["1.1.25"]="2025-05-09"
dates["1.1.29"]="2025-06-18"
dates["1.1.40"]="2025-08-15"
dates["1.1.42"]="2025-09-18"
dates["1.4.44"]="2026-04-03"
dates["1.4.46"]="2026-05-08"

# --- Function to select version ---
select_version() {
    echo "Please select which version of Elegoo Centauri Carbon firmware to download:"
    select version_choice in "${!versions[@]}"; do
        if [[ -n "$version_choice" ]]; then
            selected_version=$version_choice
            break
        else
            echo "Invalid selection. Please try again."
        fi
    done
}

# --- Main Logic ---
selected_version=""

# Check for command-line argument
if [ -n "$1" ]; then
    if [[ -n "${versions[$1]}" ]]; then
        selected_version=$1
        echo "Version $selected_version selected via command line."
    else
        echo "Invalid version '$1' provided. Please choose from the list."
        select_version
    fi
else
    select_version
fi

# --- Set Variables and Download ---
url_bin="${versions[$selected_version]}"
version_date="${dates[$selected_version]}"
file_bin="FW/FW-CentauriCarbon-v${selected_version}-${version_date}.bin"

echo
echo "Downloading Centauri Carbon Firmware version $selected_version from $version_date..."
echo

# Create FW directory if it doesn't exist
mkdir -p FW

curl "$url_bin" --output "$file_bin"
result=$(grep "<Code>NoSuchKey</Code>" "$file_bin")
file_size=$(wc -c "$file_bin" | awk '{print $1}')
echo

if [ -n "$result" ] || [ "$file_size" -le 1000000 ]; then
  rm -f "$file_bin"
  echo -e "${RED}ERROR: Cannot find an update for this model and version ${NC}"
  exit 3
else
  echo -e "${GREEN}Success! Firmware downloaded to: $file_bin${NC}"
fi
