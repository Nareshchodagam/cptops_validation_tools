#!/bin/sh
# set envs
set -o pipefail

host=$(echo $(hostname) | awk '/raphty2-.-xrd/' )
if [[ "$(hostname)" == $host ]]; then
        #xrd hosts not being used
        exit 0
fi

echo "Starting raphty"
systemctl start raphty
if [ $? -ne 0 ]; then
    echo "Failed to start raphty service"
    exit 1
fi
exit 0