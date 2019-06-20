#!/usr/bin/env bash
#
# Run this script at a sayonara node as the effective
# user 'sdb'
#
# Arguments: [ verify | verifypost | stop | start ]
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

function verifypost {
  local rc
  su - sdb -c "cd $SDB_ANT_TARGET_HOME;ls .pre_reboot_verify_failed"
  rc=$?
  if [[ $rc == 0 ]]; then
    # if the container wasn't good before the reboot, no need to
    # check it after
    echo "skip ant sdbcont.verify as container wasn't up before patching"
    su - sdb -c "cd $SDB_ANT_TARGET_HOME;rm -f .pre_reboot_verify_failed"
    rc=$?
    return $rc
  fi
 
  # Container was good before the reboot, so try to start it  
  su - sdb -c "cd $SDB_ANT_TARGET_HOME;./ant sdbcont.start"
  sleep 5

  # Now verify it, this blocks until container is up
  su - sdb -c "cd $SDB_ANT_TARGET_HOME;./ant sdbcont.verify"
  rc=$?
  
  if [[ $rc != 0 ]]; then
    echo "ant sdbcont.verify fails"
    echo "Post patch validation failed"
    return $rc
  fi

  return 0
}

function verify {
  local rc
  su - sdb -c "cd $SDB_ANT_TARGET_HOME;./ant sdbcont.verify > $SDB_ANT_TARGET_HOME/.tmp.verify.json"
  rc=$?
  
  if [[ $rc != 0 ]]; then
    su - sdb -c "cd $SDB_ANT_TARGET_HOME;touch .pre_reboot_verify_failed"
    echo "Container is not online at this node"
    echo "Will allow patch to proceed and not verify after the patch"
    rc=0
    return $rc
  fi
 
  # want to ensure there is a standby to failover to ...
  # there is an exception ... there are single node hammer 
  # environments which never have any standby's  
  su - sdb -c "cd $SDB_ANT_TARGET_HOME;cat $SDB_ANT_TARGET_HOME/.tmp.verify.json" | grep "'dbName': u'hammer" -c 
  if [[ $? -eq 0 ]]; then
    return 0
  fi
  su - sdb -c "cd $SDB_ANT_TARGET_HOME;./ant sdbcont.standbylive"
  rc=$?
  if [[ $rc != 0 ]]; then
    echo "ant sdbcont.standbylive fails"
    echo "Not suitable for patching"
    return $rc
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
elif [[ $1 == "verifypost" ]]; then
  verifypost
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
