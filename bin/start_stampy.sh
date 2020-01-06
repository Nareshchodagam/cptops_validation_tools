#!/bin/sh
# set envs
set -o pipefail

# check if stage, then start both stampy and raphty
if [[ "$(hostname)" =~ "ops0-stampy2-" ]]; then
	stage=true
fi

if [[ "$stage" = true ]]; then
    echo "Stage host"
    echo "Starting raphty"
    systemctl start raphty
    if [ $? -ne 0 ]; then
	    echo "Failed to start raphty"
	    exit 1
	fi
fi

echo "Starting stampy"
systemctl start stampy
if [ $? -ne 0 ]; then
    echo "Failed to start stampy"
    exit 1
fi
exit 0