#!/usr/bin/env bash
#
# This script is used to check if the application is alive or not
# 
STATUSCODE=$(curl --silent https://$(hostname):8443/ping.jsp)
if [ "$STATUSCODE" != "ALIVE" ]
then
echo "Looks like application is not working on the host"
exit 1
else 
echo $STATUSCODE
fi
