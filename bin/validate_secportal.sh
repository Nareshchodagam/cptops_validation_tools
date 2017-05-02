#!/bin/bash
#$Id:

ps -ef |grep -q [h]ttpd
if [ $? -eq 0 ]
then
  echo "HTTPD :        [RUNNING]"
else
  echo "ERROR HTTPD:        [NOT RUNNING]"
  exit 1
fi
