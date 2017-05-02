#!/bin/bash
# $Id: start_cmgt.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $

sleep 30

PIDFILE="/home/csbroker/cs_request_processor-data/cs_request_processor.pid"

function start_broker {
su - csbroker -c "cd /home/csbroker/cs_request_processor && bin/cs_processor start"
echo "CS Broker Processes:        [STARTED]"
}

if [ -f ${PIDFILE} ] 
  then
	  #if pidfile exists check the correct process is runnig
	  kill -0 `cat ${PIDFILE}`
	  RETVAL1=$?
	  if [ ${RETVAL1} -eq 0 ]
	    then
		   #if valid PIDFILE content is running CS BROKER is UP	
		   echo "CS Broker Processes:        [RUNNING]" 
	   else
		   #if PIDFILE PID is not running remove PIDFILE and start broker
		  rm -f ${PIDFILE}
          start_broker
		  fi
else
	#If PIDFILE missing start broker
   start_broker
fi

