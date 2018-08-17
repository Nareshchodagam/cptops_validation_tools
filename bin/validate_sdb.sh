#!/usr/bin/env bash
#
# Run this script at a sayonara node as the effective
# user 'sdb'
#
# Arguments: [ verify | stop | start ]
#
#
# verify returns 0 if this node is suitable for patching
# stop returns 0 if this nodes ./ant sdbcont.stop works
# start returns 0 if this nodes ./ant sdbcont.start works
#
# Note that all commands succeed (return 0) if no sdb installed
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
SDB_ANT_TARGET_HOME=/home/sdb/current/sfdc-base/sayonaradb/build

function verify {
  local rc
  su - sdb -c "cd $SDB_ANT_TARGET_HOME;./ant sdbcont.verify"
  rc=$?
  
  if [[ $rc != 0 ]]; then
    echo "ant sdbcont.verify fails"
    echo "Not suitable for patching"
    return 1
  fi
  
  su - sdb -c "cd $SDB_ANT_TARGET_HOME;./ant sdbcont.standbylive"
  rc=$?
  if [[ $rc != 0 ]]; then
    echo "ant sdbcont.standbylive fails"
    echo "Not suitable for patching"
    return 1
  fi
  return 0
}

function stop {
  local rc
  su - sdb -c "cd $SDB_ANT_TARGET_HOME;./ant sdbcont.stop"
  rc=$?
  return $rc
}

function start {
  local rc
  su - sdb -c "cd $SDB_ANT_TARGET_HOME;./ant sdbcont.start"
  rc=$?
  return $rc
}

###########################################################

echo "Starting $myname $1 at $HOSTNAME on $(date) ..."

if [[ "$USER" != "root" ]] ; then
  echo "Script must be run as 'root' user, not $USER user"
  exit 1
fi

# Script is a no-op if no sdb container installed
cd ${SDB_ANT_TARGET_HOME?} 2> /dev/null || { echo "Cannot cd to ${SDB_ANT_TARGET_HOME?}.  Returning 0."; exit 0; }

if [[ $1 == "verify" ]]; then
  verify
elif [[ $1 == "stop" ]]; then
  stop
elif [[ $1 == "start" ]]; then
  start
else
  false
fi
rc=$?

echo "$myname $1 returning $rc"
exit $rc
