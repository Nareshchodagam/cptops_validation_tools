#!/bin/bash
#
# Script confirms current server is Nagios Standby and not primary.
#
#
domain=`echo $HOSTNAME | awk -F - '{print $4}'`
pod=`echo $HOSTNAME | awk -F - '{print $1}'`
prim_serv=`dig $pod-monitor-$domain +short | head -1`

# Test if current server is standby against DNS.
if [ "$prim_serv" = "$HOSTNAME." ]; then
    /etc/init.d/nagios start
fi
