#!/bin/bash
# validate_stride.sh 2020-17-03 naresh.ch@SFDC.NET

function running1 {

 systemctl is-active --quiet stride
  if [ $? -eq 0 ]
  then
        echo "YES" > ~/Put-Status.txt
        echo "STRIDE: [RUNNING]"
        exit 0
  else
         echo "NO" > ~/Put-Status.txt
         echo "${HOSTNAME}:STRIDE: [DEPLOYED but not RUNNING]"
        exit 0
  fi

}

function Pre_status {

RPM_CHECK=$(rpm -qa | grep stride); RETVAL=$?
if [ ${RETVAL} -eq 0 ]
        then
        running1
else
      echo "NO" > ~/Put-Status.txt
      echo "STRIDE:  [NOT DEPLOYED - skipping check] "
        exit 0
fi

}

function running2 {

sleep 60
n=0
until [ $n -ge 5 ]
do
 systemctl is-active --quiet stride
  if [ $? -eq 0 ]
  then
        RETVAL1=0
        echo "STRIDE: [RUNNING]"
        exit 0
  else
         RETVAL1=1
         echo "${HOSTNAME}:STRIDE: [DEPLOYED but not RUNNING]. Checking again in 2 min"
         n=$[$n+1]
         sleep 2m
  fi
done

[ "$RETVAL1" -eq 1 ] && echo "${HOSTNAME}: STRIDE: [FAILED TO START]. Contact @stride - Host Integrity and @Hardening Team"
exit 1

}

function Post_status {

RPM_CHECK=$(rpm -qa | grep stride); RETVAL=$?
GET_Status=$(<~/Put-Status.txt)

if [ ${RETVAL} -eq 0 ] && [ "$GET_Status" != 'NO' ]
        then
        running2
else
        echo "STRIDE:  [NOT DEPLOYED - skipping check] "
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
