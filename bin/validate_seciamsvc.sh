#!/bin/bash
# validate_seciamsvc.sh 2018-12-05 snolan@SFDC.NET
# Implemented seciamsvc status caputer logic 2019-07-30 naresh.ch@SFDC.NET

function running1 {

 systemctl is-active --quiet seciamsvc
  if [ $? -eq 0 ]
  then
        echo "YES" > ~/Put-Status.txt
        echo "SECIAMSVC: [RUNNING]"
        exit 0
  else
         echo "NO" > ~/Put-Status.txt
         echo "${HOSTNAME}:SECIAMSVC: [DEPLOYED but not RUNNING]"
        exit 0
  fi

}

function Pre_status {

RPM_CHECK=$(rpm -qa | grep seciamsvc); RETVAL=$?
if [ ${RETVAL} -eq 0 ]
        then
        running1
else
      echo "NO" > ~/Put-Status.txt
      echo "SECIAMSVC:  [NOT DEPLOYED - skipping check] "
        exit 0
fi

}

function running2 {

sleep 60
n=0
until [ $n -ge 5 ]
do
 systemctl is-active --quiet seciamsvc
  if [ $? -eq 0 ]
  then
        RETVAL1=0
        echo "SECIAMSVC: [RUNNING]"
        exit 0
  else
         RETVAL1=1
         echo "${HOSTNAME}:SECIAMSVC: [DEPLOYED but not RUNNING]. Checking again in 2 min"
         n=$[$n+1]
         sleep 2m
  fi
done
start_seciamsvc
}

function start_seciamsvc {

 systemctl restart seciamsvc 
 sleep 10
 systemctl is-active --quiet seciamsvc 
 if [ $? -eq 0 ]
then 
 echo "SECIAMSVC:[RUNNING]"; 
 exit 0
else 
 echo "${HOSTNAME}: SECIAMSVC: [FAILED TO START]. Contact @SecDS - Secured Directory Services and @Hardening"
exit 1
fi

}


function Post_status {

RPM_CHECK=$(rpm -qa | grep seciamsvc); RETVAL=$?
GET_Status=$(<~/Put-Status.txt)

if [ ${RETVAL} -eq 0 ] && [ "$GET_Status" != 'NO' ]
        then
        running2
else
        echo "SECDIAMSVC:  [NOT DEPLOYED - skipping check] "
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
