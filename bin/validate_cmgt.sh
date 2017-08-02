#!/bin/bash
#$Id: validate_cmgt.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $

PIDFILE="/home/csbroker/cs_request_processor-data/cs_request_processor.pid"

if [ -f ${PIDFILE} ] 
  then
	  #if pidfile exists check the correct process is running
	  kill -0 `cat ${PIDFILE}`
	  RETVAL1=$?
	  if [ ${RETVAL1} -eq 0 ]
	    then
		   #if valid PIDFILE content is running CS BROKER is UP	
		   echo "CS Broker Processes:        [RUNNING]" 
	   else
		   #if PIDFILE PID mismatch
		  echo "ERROR CS Broker Processes:        [WRONG PID FOUND]"
		  fi
else
	#If PIDFILE missing
    echo "ERROR CS Broker Processes:        [NOT RUNNING]"
fi
