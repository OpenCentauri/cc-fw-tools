#!/opt/bin/bash
#
# Synchronize time to NTP, and every 24 hours!
#
#
if [ $# -eq 1 ]; then
    OC_NTP_SERVER="$1"
else
    OC_NTP_SERVER="pool.ntp.org"
fi

# Wait a few seconds for wifi to come up before trying the first time
sleep 5

# Try and sync 
while [ 1 ]; do
    echo -n "Attempting to sync initial time... "
    /app/ntpdate $OC_NTP_SERVER
    if [ $? -ne 0 ]; then
        echo "Failed, sleeping and trying again..."
    else
        echo "Successful first sync! Starting delay loop..."
	break
    fi
    sleep 1
done

while [ 1 ]; do
    sleep 86400
    /app/ntpdate $OC_NTP_SERVER
done
