#!/bin/bash

#Script to check|stop|start gomon service
OS_VERSION=`rpm -q --queryformat '%{VERSION}' centos-release`

case "$1" in
    
    'stop')
        if [ $OS_VERSION -eq 7 ]; then
            /usr/bin/systemctl stop gomon
        else
            /sbin/stop gomon
        fi
    ;;
    'start')
        if [ $OS_VERSION -eq 7 ]; then
            /usr/bin/systemctl start gomon
        else
            /sbin/start gomon
        fi
    ;;
    'status')
        if [ $OS_VERSION -eq 7 ]; then
            /usr/bin/systemctl status gomon
        else
            /sbin/status gomon
        fi
    ;;
esac
