#!/bin/sh
# set envs
set -o pipefail
# check if stage environment
if [[ "$(hostname)" =~ "ops0-stampy2-" ]]; then
	stage=true
fi

if [[ "$stage" = true ]]; then
	echo "Stop raphty"
	systemctl stop raphty
	if [ $? -ne 0 ]; then
	    echo "Failed to stop raphty"
	    exit 1
	else
		echo "Successfully stopped raphty"
	fi
fi

echo "Stop stampy"
systemctl stop stampy
if [ $? -ne 0 ]; then
    echo "Failed to stop stampy"
    exit 1
else
	echo "Successfully stopped stampy"
fi

# sleep
sleep 2s

# verify if the service is still running
if [[ "$stage" = true ]]; then
	resp="$(raphtyctl status)"
	cmdstatus=${PIPESTATUS[0]}
	if [ "$cmdstatus" -eq 0 ];
	then
		echo "Fail: raphty still running"
		exit 1
	fi
fi
# verify for stampy
resp="$(stampyctl status)"
cmdstatus=${PIPESTATUS[0]}
if [ "$cmdstatus" -eq 0 ];
then
	echo "Fail: stampy still running"
	exit 1
fi
exit 0