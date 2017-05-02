#!/bin/bash
# $Id: validate_polcore.sh 241805 2016-11-28 16:30:28Z iviscio@SFDC.NET $
function running {

sleep 60
n=0
until [ $n -ge 5 ]
do
  su - ilo-pce -c "/opt/illumio-pce/illumio-pce-ctl status"
  if [ $? -eq 1 ]
  then
	  RETVAL1=0
      break
  else
	 RETVAL1=1
	 echo "${HOSTNAME}:Illumio not running. Checking again in 1 min"
	 n=$[$n+1]
     sleep 60
  fi
done

[ "$RETVAL1" -eq 1 ] && echo "${HOSTNAME}: Illumio failed to start in > 5min. Please contact SysSec to troubleshoot"

}

running

#Temporary Disable CHARON check until is LIVE
#CHECK_CHARON=$(ps -ef|grep [c]haron); RETVAL2=$?
#if [ ${RETVAL1} -eq 0 ] && [ ${RETVAL2} -eq 0 ]
if [ ${RETVAL1} -eq 0 ]
        then
        echo "Illumio Processes:        [RUNNING]"
else
        echo "ERROR Illumio Processes:        [NOT RUNNING]"
        exit 1
fi