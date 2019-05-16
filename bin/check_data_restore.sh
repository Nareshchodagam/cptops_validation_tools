#!/usr/bin/env bash
#
# This script is used to check if any Data is being restored using this server.
# 
#
ps -ef | grep -i java |grep -v grep >/dev/null 2>&1
if [ $? -ne 0 ]
then 
echo "No ongoing Data restore , continue patching"
exit 0
else 
echo "Looks like Data restore is inprogress on this host , contact SiteReliability "
exit 1
fi
