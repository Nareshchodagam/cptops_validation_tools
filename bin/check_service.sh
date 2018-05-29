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
if [ $PROCESS_CHECK  -eq 0 ]; then
   echo "gomon is not running!"
else
   echo "gomon is running!"
fi
;;
esac

