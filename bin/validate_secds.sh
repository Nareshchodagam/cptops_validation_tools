#!/bin/bash
# validate_secds.sh 2018-12-05 snolan@SFDC.NET

function running {

sleep 10
n=0
until [ $n -ge 5 ]
do
 systemctl is-active --quiet secds
  if [ $? -eq 0 ]
  then
        RETVAL1=0
        echo "SECDS: [RUNNING]"
        exit 0
  else
         RETVAL1=1
         echo "${HOSTNAME}:SECDS: [DEPLOYED but not RUNNING]. Checking again in 1 min"
         n=$[$n+1]
         sleep 60
  fi
done

[ "$RETVAL1" -eq 1 ] && echo "${HOSTNAME}: SECDS: [FAILED TO START]. Contact @SecDS - Secured Directory Services and @Hardening"
exit 1

}


RPM_CHECK=$(rpm -qa | grep secds); RETVAL=$?
if [ ${RETVAL} -eq 0 ]
        then
        running
else
        echo "SECDS:  [NOT DEPLOYED - skipping check] "
        exit 0
fi
