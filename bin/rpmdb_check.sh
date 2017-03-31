#!/bin/bash

# Script to remove RPM Corrupt DB from Host

PIDS=`ps -ef | grep -i yum  | grep -v grep| awk '{ print $2 }' | tr '\n' ' '`
RPMDB="/var/lib/rpm/__db.00*"
RPMLOCK="/var/lib/rpm/.rpm.lock"


function rpmdbremove {
    echo "RPMDB Seems Corrupt, Removing RPMDB..."
    /bin/rm -rf $RPMDB

    echo "Removing RPM Lock File..."
    /bin/rm -rf $RPMLOCK
}

function rpmdbcreate {
    echo "Recreating RPM DB..."
    /bin/rpm --rebuilddb
}

function verifyrpmdb {
    /bin/rpm --verifydb &
    TASKPID=$!
    sleep 10
    kill -s 0 $TASKPID 2>> /dev/null
    if [ $? -eq 0 ]; then
        kill -9 $TASKPID
        RPMVERIFY=1
    else
        wait $TASKPID
        RPMVERIFY=$?
    fi

    if [ "$RPMVERIFY" -ne "0" ]; then
        rpmdbremove
        rpmdbcreate
    else
        echo "RPMDB is not Corrupt."
    fi
}

function yumcheck {
   if [ -z "$PIDS" ]; then
       echo "YUM is not Running."
       echo "Anyways Cleaning Yum..."
       /usr/bin/yum clean all
       EXITYUM="0"
   else
        echo "Killing PID's $PIDS"
        kill -9 $PIDS
        echo "Cleaning Yum..."
        /usr/bin/yum clean all
        EXITYUM="1"
   fi
}

#Main

echo "Verifying RPMDB Integrity..."
verifyrpmdb

echo "Checking if YUM is Already Running..."
yumcheck

if [ "$EXITYUM" -ne "0" ]; then
    echo "Checking RPMDB Integrity After the YUM PID KILL..."
    verifyrpmdb
fi

exit 0