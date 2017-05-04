#!/bin/bash
#$Id: validate_vc.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $
ps -ef |grep -q [s]vnserve
if [ $? -eq 0 ]
then
  echo "Process SVNSERVE:        [RUNNING]"
else
  echo "ERROR Process SVNSERVE:        [NOT RUNNING]"
  exit 1
fi
