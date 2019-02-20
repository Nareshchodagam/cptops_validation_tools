#!/bin/bash

set -x

SERVICES='storm-nimbus storm-ui storm-supervisor'
SYSTEMD_PATH="/etc/systemd/system"

for service in ${SERVICES}
do
    if [ -f "${SYSTEMD_PATH}/${service}.service" ]; then
        echo "*** stopping ${service}"
        service ${service} stop
    fi
done
