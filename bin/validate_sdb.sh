#!/bin/bash
# Return 0 if this node is suitable for CPT patching
# Return 1 otherwise
#
# Run this script at a sayonara node as the effective
# user 'sdb'
#
# Suitable for patching means that should this node be rebooted
# as a result of a CPT delivered OS patch
# then there will not be a database outage
# other than a possible failover to another
# sdb host supporting this database
#
# Script will check that the required sdb package is
# installed, if not, will return 0 (as this node
# is suitable for CPT patching).
#
# If sdb packages are installed, will ensure that
# sdb is healthy here
# If sdb is not healthy here, will return 1
#
# If sdb is healthy here, will ensure there is
# at least 1 active standby
# If there is not at least 1 active standby, return 1
#

myname=$(basename "$0")
echo "Starting $myname at $HOSTNAME on $(date) ..."

if [[ "$USER" != "sdb" ]] && [[ "$USER" != "root" ]] ; then
    echo "Script must be run as 'sdb' or 'root' user"
    exit 1
fi

# Location of the sdb ant targets
SDB_ANT_TARGET_HOME=/home/sdb/current/sfdc-base/sayonaradb/build
# If does not exist, then simply return successfully
#  since this implies that there is no sdb installed here
#  and thus this node can be patched by CPT as any patching
#  will certainly not cause an sdb outage
cd ${SDB_ANT_TARGET_HOME?} || { echo "Cannot cd to ${SDB_ANT_TARGET_HOME?}"; exit 0; }
cd ${SDB_ANT_TARGET_HOME?};./ant sdbcont.verify > /dev/null 2> /dev/null
rc=$?

if [[ $rc != 0 ]]; then
    echo "ant sdbcont.verify fails"
    echo "Not suitable for patching"
    exit 1
fi

cd ${SDB_ANT_TARGET_HOME?};./ant sdbcont.standbylive > /dev/null 2> /dev/null
rc=$?
if [[ $rc != 0 ]]; then
    echo "ant sdbcont.standbylive fails"
    echo "Not suitable for patching"
    exit 1
fi

echo "Suitable for patching"
exit 0
