#!/bin/bash

#Script to check|stop|start gomon service
PROCESS_CHECK=`ps -ef | grep -v grep | grep gomon | wc -l`
OS_VERSION=`rpm -q --queryformat '%{VERSION}' centos-release`

case "$1" in
    
    'stop')
        if [ $PROCESS_CHECK  -eq 0 ]; then
            echo "gomon is not running!!"
        else
            if [ $OS_VERSION -eq 7 ]; then
                /usr/bin/systemctl stop gomon
            else
                /sbin/stop gomon
            fi
        fi
        ERR=$?
        if [ $ERR -ne 0 ]; then
            exit $ERR
        fi

        if [ $OS_VERSION -eq 7 ]; then
            /usr/bin/systemctl stop cms-ant
        else
            /sbin/service cms-ant stop
        fi
    ;;
    'start')
        if [ $PROCESS_CHECK -gt 0 ]; then
            echo "gomon is running!!"
        else
            if [ $OS_VERSION -eq 7 ]; then
                /usr/bin/systemctl start gomon
            else
                /sbin/start gomon
            fi
        fi
    ;;
    'status')
        if [ $OS_VERSION -eq 7 ]; then
            /usr/bin/systemctl status gomon
        else
            /sbin/status gomon
        fi
        # the above gomon status check exits 0 whether or not gomon is running...
        # so, no point checking the exit code.  of informational value only

        if [ $OS_VERSION -eq 7 ]; then
            /usr/bin/systemctl status cms-ant
        else
            /sbin/service cms-ant status
        fi
    ;;
esac
