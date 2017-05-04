#!/bin/bash
#$Id: validate_nsm.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $
ps -ef |grep -q [b]ro
if [ $? -eq 0 ]
then
  echo "Process BRO:        [RUNNING]"
else
  echo "ERROR Process BRO:        [NOT RUNNING]"
  exit 1
fi
