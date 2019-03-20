#!/bin/sh
# set envs
set -o pipefail

host=$(echo $(hostname) | awk '/raphty2-.-xrd/' )
if [[ "$(hostname)" == $host ]]; then
        #xrd hosts not being used
        exit 0
fi

# verify the status of the service
resp="$(raphtyctl status)"
cmdstatus=${PIPESTATUS[0]}
if [ "$cmdstatus" -ne 0 ];
then
	echo "Failed to get the status"
	exit 1
fi
echo "Raphty service is running successfully"
exit 0