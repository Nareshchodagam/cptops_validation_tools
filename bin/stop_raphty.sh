#!/bin/sh
# set envs
set -o pipefail

host=$(echo $(hostname) | awk '/raphty2-.-xrd/' )
if [[ "$(hostname)" == $host ]]; then
        #xrd hosts not being used
        exit 0
fi

echo "Stop raphty"
systemctl stop raphty
if [ $? -ne 0 ]; then
    echo "Failed to stop raphty"
    exit 1
else
	echo "Successfully stopped raphty"
fi

# sleep
sleep 2s

# verify if raphty is still running
resp="$(raphtyctl status)"
cmdstatus=${PIPESTATUS[0]}
if [ "$cmdstatus" -eq 0 ];
then
	echo "Failed: raphty is still running"
	exit 1
fi
exit 0