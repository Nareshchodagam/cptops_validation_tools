#!/bin/sh
# set envs
set -o pipefail

# verify the status of the service
resp="$(stampyctl status)"
cmdstatus=${PIPESTATUS[0]}
if [ "$cmdstatus" -ne 0 ];
then
	echo "Failed to get the status"
	exit 1
fi

# for stampy, check if kms or netHSM works by sending a sign request
if [[ "$(hostname)" =~ "stampy" ]]; then
	signResp="$(stampyctl --server https://$(hostname):7865 sign testpgp)"
	status=${PIPESTATUS[0]}
	if [ "$status" -ne 0 ];
	then
		echo "Test sign request failed."
		exit 1
	else
		echo "Test sign request succeeds."
	fi
fi
exit 0