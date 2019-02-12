#!/bin/bash
# validate_secds.sh 2019-01-28 naresh.ch@SFDC.NET
function running {

 systemctl is-active --quiet secds
  if [ $? -eq 0 ]
  then
        echo "YES" > ~/Put-Status.txt
        echo "SECDS: [RUNNING]"
        exit 0
  else
         echo "NO" > ~/Put-Status.txt
         echo "${HOSTNAME}:SECDS: [DEPLOYED but not RUNNING]"
        exit 0
  fi

}

RPM_CHECK=$(rpm -qa | grep secds); RETVAL=$?
if [ ${RETVAL} -eq 0 ]
        then
        running
else
      echo "NO" >  ~/Put-Status.txt
      echo "SECDS:  [NOT DEPLOYED - skipping check] "
        exit 0
fi
