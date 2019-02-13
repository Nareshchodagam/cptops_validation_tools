#!/bin/bash
# validate_secds.sh 2018-12-05 snolan@SFDC.NET
# Implemented secds status caputer logic 2019-02-8 naresh.ch@SFDC.NET

function running1 {

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

function Pre_status {

RPM_CHECK=$(rpm -qa | grep secds); RETVAL=$?
if [ ${RETVAL} -eq 0 ]
        then
        running1
else
      echo "NO" > ~/Put-Status.txt
      echo "SECDS:  [NOT DEPLOYED - skipping check] "
        exit 0
fi

}

function running2 {

sleep 60
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
         echo "${HOSTNAME}:SECDS: [DEPLOYED but not RUNNING]. Checking again in 2 min"
         n=$[$n+1]
         sleep 2m
  fi
done

[ "$RETVAL1" -eq 1 ] && echo "${HOSTNAME}: SECDS: [FAILED TO START]. Contact @SecDS - Secured Directory Services and @Hardening"
exit 1

}

function Post_status {

RPM_CHECK=$(rpm -qa | grep secds); RETVAL=$?
GET_Status=$(<~/Put-Status.txt)

if [ ${RETVAL} -eq 0 ] && [ "$GET_Status" != 'NO' ]
        then
        running2
else
        echo "SECDS:  [NOT DEPLOYED - skipping check] "
        exit 0
fi
}

if [  $# -eq 0 ]
then
  echo "Usage: $0 Pre_status|Post_status"
  exit 1
else
  $1
fi
