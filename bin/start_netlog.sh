#!/bin/bash

SERVICES='mongodb elasticsearch graylog http-graylog-health gelf-health gelf-storm-log-health tcp-syslog-health'
SYSTEMD_PATH="/etc/systemd/system"

for service in ${SERVICES}
do
    if [ -f "${SYSTEMD_PATH}/${service}.service" ]; then
        echo "*** starting ${service}"
        service ${service} start
    fi
done
