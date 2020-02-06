#!/bin/bash
#$Id: validate_vc.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $
#checking if svnserve is enabled then it should be running
if [[ `systemctl is-enabled svnserve` == enabled ]]
then
  systemctl is-active --quiet svnserve
  if [ $? -eq 0 ]
  then
    echo "Process SVNSERVE:        [RUNNING]"
  else
    echo "ERROR Process SVNSERVE:        [NOT RUNNING]"
    exit 1
  fi
fi

#checking httpd

systemctl is-active --quiet httpd
if [ $? -eq 0 ]
then
  echo "Process HTTPD:        [RUNNING]"
else
  echo "ERROR Process HTTPD:        [NOT RUNNING]"
  exit 1
fi
