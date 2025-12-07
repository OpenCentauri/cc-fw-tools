#!/bin/bash

# check the parameters
if [ $# != 2 ]; then
  echo "usage : $0 <project_root> <uart_package>"
  exit 1
fi

project_root="$1"
uart_package="$2"

source "$project_root/TOOLS/helpers/utils.sh" "$project_root"

check_tools "unzip"

# check the project root folder
if [ ! -d "$project_root" ]; then
  echo -e "${RED}ERROR: Cannot find the folder '$project_root' ${NC}"
  exit 3
fi

# check the uart package folder
uart_package_folder="${OPTIONS_DIR}/uart/${uart_package}"
if [ ! -d "$uart_package_folder" ]; then
  echo -e "${RED}ERROR: Cannot find the folder '$uart_package_folder' ${NC}"
  exit 4
fi

# check the uart package file exists uart.zip or package
uart_zip_file="${uart_package_folder}/uart.zip"
if [ ! -f "$uart_zip_file" ]; then
  echo -e "${RED}ERROR: Cannot find the file '$uart_zip_file' ${NC}"
  exit 5
fi

# check the target folder
target_folder="$project_root/unpacked"
if [ ! -d "$target_folder" ]; then
  echo -e "${RED}ERROR: Cannot find the target folder '$target_folder' ${NC}"
  exit 6
fi

echo -e "${YELLOW}INFO: Copying the uart files ...${NC}"
echo -e "${YELLOW}INFO: Copying the uart files to $target_folder ...${NC}"

# Unzip the uart package into the target folder
unzip -oqq "$uart_zip_file" -d "$target_folder"

# Check if unzip succeeded
if [ $? -ne 0 ]; then
  echo -e "${RED}ERROR: Failed to unzip the uart package ${NC}"
  exit 7
fi

# Overwrite the inittab file
echo -e "${YELLOW}INFO: Overwriting the inittab file ...${NC}"

cat <<EOF >"$ROOTFS_DIR/etc/inittab"
::sysinit:/etc/init.d/rcS S boot
::shutdown:/etc/init.d/rcS K shutdown
::askconsole:/bin/ash --login
EOF

echo -e "${GREEN}INFO: The UART package has been installed. Version: $uart_package ${NC}"

exit 0
