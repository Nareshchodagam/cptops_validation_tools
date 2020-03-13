#!/bin/bash
#$Id: validate_secmgt.sh 2
#checking if syssec_build_precheck is enabled then it should be running
if [[ `systemctl is-enabled syssec_build_precheck` == enabled ]]
then
  systemctl is-active --quiet syssec_build_precheck
  if [ $? -eq 0 ]
  then
    echo "Process syssec_build_precheck:        [RUNNING]"
  else
    echo "ERROR Process syssec_build_precheck:        [NOT RUNNING]"
    exit 1
  fi
fi

