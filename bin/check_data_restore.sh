#!/usr/bin/env bash
#
# This script is used to check if any Data is being restored using this server.
# 
#
ps -fu sfdc | grep -v UID >/dev/null 2>&1
if [ $? -ne 0 ]
then 
echo "No ongoing Data restore , continue patching"
exit 0
else 
echo "SFDC JAVA process is running, looks like Data restore is inprogress on this host , please halt patching on this host. Contact Service Owner."
exit 1
fi
