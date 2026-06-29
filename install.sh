#!/bin/bash

usernaappuser="root"
port="22"
stage=0
flash=0

if [ $# -ne 2 ] || (! [ "$1" = "--stage" ] && ! [ "$1" = "--flash" ] && ! [ "$1" = "--sendit" ]); then
    echo "Usage:"
    echo "  $0 --stage <printer-ip>  # Stage files on the printer for flashing"
    echo "  $0 --flash <printer-ip>  # Flash the staged files on the printer"
    echo "  $0 --sendit <printer-ip> # Stage files on the printer and then flash"
    exit 1
fi

if [ "$1" = "--stage" ]; then
    stage=1
elif [ "$1" = "--flash" ]; then
    flash=1
elif [ "$1" = "--sendit" ]; then
    stage=1
    flash=1
else
    echo "Unknown arguappusernt... Exiting"
    exit 1
fi

ip="$2"

# SCP file transfer
if [ $stage -eq 1 ]; then
    # Only do this step for stage and sendit
    #echo "Mounting exUDISK if necessary and mapping old UDISK to exUDISK..."
    #ssh -p $port $usernaappuser@$ip 'mount -t vfat,exfat -o iocharset=utf8 /dev/sda1 /mnt/exUDISK ; mount --bind /mnt/exUDISK /user-resource'
    echo "Uploading..."
    scp -o StrictHostKeyChecking=no -P $port update/update.swu $usernaappuser@$ip:/user-resource
fi
if [ $stage -eq 1 ] || [ $flash -eq 1 ]; then
    # Do this step for both stage, flash and sendit
    # MD5 Calculation
    md5sum_local=$(md5sum update/update.swu | awk '{ print $1 }')
    echo "MD5 Local : $md5sum_local"
    md5sum_remote=$(ssh -p $port $usernaappuser@$ip "md5sum /user-resource/update.swu" | awk '{ print $1 }')
    echo "MD5 Remote: $md5sum_remote"
    if ! [[ "$md5sum_remote" == "$md5sum_local" ]]; then
        # If MD5 checksums don't match, delete the file and retry
        ssh -p $port $usernaappuser@$ip 'rm -f /user-resource/update.swu'
        echo "FAILED!"
        exit 1
    fi
    #echo "Mapping old UDISK to exUDISK..."
    #ssh -p $port $usernaappuser@$ip 'mount --bind /mnt/exUDISK /user-resource'
    # Getting boot partition and updating firmware
    current_boot_partition=$(ssh -p $port $usernaappuser@$ip "fw_printenv boot_partition" | awk -F= '{ print $2 }' | tr -d '[:space:]')
    boot_partition="now_B_next_A"
    if [[ "$current_boot_partition" == "bootA" ]]; then
        boot_partition="now_A_next_B"
    fi
fi
if [ $flash -eq 1 ]; then
    # Only do this step for flash and sendit
    # Update firmware, actually run the swupdate_cmd!!!
    echo "Updating..."
    ssh -p $port $usernaappuser@$ip "tail -F /user-resource/swupdate.log" < /dev/null &
    ssh -p $port $usernaappuser@$ip "swupdate_cmd.sh -i /user-resource/update.swu -e stable,${boot_partition} -k /etc/swupdate_public.pem"
else
    echo "To tail log in a different window:"
    echo ssh -p $port $usernaappuser@$ip "tail -F /user-resource/swupdate.log"
    echo "Run command manually to complete flash:"
    echo ssh -p $port $usernaappuser@$ip "swupdate_cmd.sh -i /user-resource/update.swu -e stable,${boot_partition} -k /etc/swupdate_public.pem"
    echo "Or use this script again to commit:"
    echo ./install.sh $ip --flash
fi
echo "SUCCESS!"
exit 0

