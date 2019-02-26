#!/bin/bash

set -x

SERVICES='storm-nimbus storm-ui storm-supervisor'
SYSTEMD_PATH="/etc/systemd/system"

VALIDATED="TRUE"

for service in ${SERVICES}
do
    if [ -f "${SYSTEMD_PATH}/${service}.service" ]; then
        echo "*** checking that ${service} is running"
        service ${service} status
        if [ "$?" != 0 ]; then
            echo -e '\tSERVICE ${service} is not running'
            VALIDATED="FALSE"
        fi
    fi
done

if [ "${VALIDATED}" == "TRUE" ]; then
    echo "*** validation for netevents on `hostname` succeeded"
    exit 0
else
    echo "*** validation for netevents on `hostname` failed!"
    exit 1
fi
