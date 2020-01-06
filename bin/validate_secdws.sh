#!/bin/bash
# validate_secdws.sh 2019-07-30 naresh.ch@SFDC.NET

function running1 {

 systemctl is-active --quiet secdws
  if [ $? -eq 0 ]
  then
        echo "YES" > ~/Put-Status1.txt
        echo "SECDWS: [RUNNING]"
        exit 0
  else
         echo "NO" > ~/Put-Status1.txt
         echo "${HOSTNAME}:SECDWS: [DEPLOYED but not RUNNING]"
        exit 0
  fi

}

function Pre_status {

RPM_CHECK=$(rpm -qa | grep secdws); RETVAL=$?
if [ ${RETVAL} -eq 0 ]
        then
        running1
else
      echo "NO" > ~/Put-Status1.txt
      echo "SECDWS:  [NOT DEPLOYED - skipping check] "
        exit 0
fi

}

function running2 {

sleep 60
n=0
until [ $n -ge 5 ]
do
 systemctl is-active --quiet secdws
  if [ $? -eq 0 ]
  then
        RETVAL1=0
        echo "SECDWS: [RUNNING]"
        exit 0
  else
         RETVAL1=1
         echo "${HOSTNAME}:SECDWS: [DEPLOYED but not RUNNING]. Checking again in 2 min"
         n=$[$n+1]
         sleep 2m
  fi
done
start_secdws
}

function start_secdws {

 systemctl restart secdws 
 sleep 10
 systemctl is-active --quiet secdws
 if [ $? -eq 0 ]
then 
 echo "SECDWS:[RUNNING]"; 
 exit 0
else 
 echo "${HOSTNAME}: SECDWS: [FAILED TO START]. Contact @SecDS - Secured Directory Services and @Hardening"
exit 1
fi

}


function Post_status {

RPM_CHECK=$(rpm -qa | grep secdws); RETVAL=$?
GET_Status=$(<~/Put-Status1.txt)

if [ ${RETVAL} -eq 0 ] && [ "$GET_Status" != 'NO' ]
        then
        running2
else
        echo "SECDWS:  [NOT DEPLOYED - skipping check] "
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
