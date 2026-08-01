#!/bin/bash -x
#
# Script to run through all the firmware extract, patch and build steps!
#

project_root="$PWD"

# Source the utils.sh file
source "$project_root/TOOLS/helpers/utils.sh" "$project_root"

# --- Firmware Selection ---
#DEFAULT_FW="FW/FW-CentauriCarbon-v1.1.25-2025-05-09.bin"
#DEFAULT_FW="FW-CentauriCarbon-v1.1.40-2025-08-15.bin"
[[ -z "$1" ]] && VERSION="1.4.49" || VERSION="$1"
FIRMWARE_FILE=""
PATCH_LIST="$project_root/unpacked/.oc-patches-applied.json"
sudo rm -f "$PATCH_LIST"

if [ -n "$VERSION" ]; then
    # Argument provided, try to find a matching firmware file
    #VERSION=$1
    # Use a loop to safely handle the glob pattern and find the first match
    for f in FW/FW-CentauriCarbon-v${VERSION}-*.bin; do
        if [ -e "$f" ]; then
            FIRMWARE_FILE="$f"
            break # Found a match, exit loop
        fi
    done

    if [ -z "$FIRMWARE_FILE" ]; then
        echo "Error: No firmware file found in FW/ for version '$VERSION'."
        echo "Please make sure the file exists and is named correctly (e.g., FW/FW-CentauriCarbon-v${VERSION}-YYYY-MM-DD.bin)"
        exit 1
    fi
    echo "Using specified firmware version: $FIRMWARE_FILE"
else
    # No argument provided, use the default
    FIRMWARE_FILE=$DEFAULT_FW
    echo "No version specified, using default firmware: $FIRMWARE_FILE"
fi

if [ ! -f "$FIRMWARE_FILE" ]; then
    echo "Error: Firmware file not found: $FIRMWARE_FILE"
    echo "Please run ./fwdl.sh to download firmware first."
    exit 1
fi
echo

# files needed
FILES="sw-description sw-description.sig boot-resource uboot boot0 kernel rootfs dsp0 cpio_item_md5"

# check the required tools
check_tools "grep md5sum openssl wc awk sha256sum mksquashfs git git-lfs"

echo "Unpacking the firmware..."
sudo ./unpack.sh "$FIRMWARE_FILE"
if [ $? -ne 0 ]; then
    echo "Error unpacking the firmware, aborting..."
    exit 1
fi
echo

echo "Patching the firmware..."
sudo env \
    "OC_BUILD_BRANCH=${OC_BUILD_BRANCH:-}" \
    "OC_BUILD_COMMIT=${OC_BUILD_COMMIT:-}" \
    "OC_BUILD_DIRTY=${OC_BUILD_DIRTY:-}" \
    python3 ./oc-patches/patch_planner.py "$VERSION" --patch-list "$PATCH_LIST"
if [ $? -ne 0 ]; then
    echo "Error patching the firmware, aborting..."
    exit 1
fi
if [ ! -s "$PATCH_LIST" ]; then
    echo "Error: Patching completed without producing a patch list, aborting..."
    exit 1
fi
echo

echo "Re-packing the firmware into update/update.swu..."
sudo ./pack.sh
if [ $? -ne 0 ]; then
    echo "Error re-packing the firmware, aborting..."
    exit 1
fi

echo "Creating update/manifest.json..."
sudo env \
    "OC_BUILD_BRANCH=${OC_BUILD_BRANCH:-}" \
    "OC_BUILD_COMMIT=${OC_BUILD_COMMIT:-}" \
    "OC_BUILD_DIRTY=${OC_BUILD_DIRTY:-}" \
    python3 ./TOOLS/create_manifest.py \
    --original "$FIRMWARE_FILE" \
    --patch-list "$PATCH_LIST" \
    --final update/update.swu \
    --output update/manifest.json \
    --repo-root "$project_root"
if [ $? -ne 0 ]; then
    echo "Error creating the firmware manifest, aborting..."
    exit 1
fi
echo "Naming final firmware artifact from manifest metadata..."
sudo python3 ./TOOLS/finalize_firmware_artifact.py \
    --manifest update/manifest.json \
    --firmware update/update.swu \
    --output-dir update
if [ $? -ne 0 ]; then
    echo "Error naming the final firmware artifact, aborting..."
    exit 1
fi
echo "Creating update/patches.md..."
sudo python3 ./TOOLS/create_patch_summary.py \
    --manifest update/manifest.json \
    --output update/patches.md
if [ $? -ne 0 ]; then
    echo "Error creating the patch summary, aborting..."
    exit 1
fi
sudo rm -f "$PATCH_LIST"
#echo "Packing the firmware into update/force_upgrade.bin..."
#sudo ./fup.sh
echo
