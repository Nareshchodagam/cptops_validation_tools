#!/bin/bash
# $Id: start_cmgt.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $

####################################################################################
#
# Please contact the Certificate Service group for any info about this script
# https://gus.my.salesforce.com/0F9B00000006LcG
# 
# To test this script in the Cert Service DEV infrastructure just define CMGT_ROOT
# and CMGT_PREPROCESSOR_ROOT to point to the tested services instances. 
#
####################################################################################

sleep 30

CMGT_ROOT="/home/csbroker"
CMGT_PREPROCESSOR_ROOT="/home/csbroker"

PIDFILE="${CMGT_ROOT}/cs_request_processor-data/cs_request_processor.pid"
PIDFILE_PREPROCESSOR="${CMGT_PREPROCESSOR_ROOT}/cs_request_preprocessor-data/cs_request_preprocessor.pid"

function start_broker {
su - csbroker -c "cd ${CMGT_ROOT}/cs_request_processor && bin/cs_processor.sh start"
echo "CS Broker Processes:        [STARTED]"
sleep 10
}

function start_preprocessor {
su - csbroker -c "cd ${CMGT_PREPROCESSOR_ROOT}/cs_request_preprocessor && bin/cs_preprocessor.sh start"
echo "CS Preprocessor Processes:        [STARTED]"
sleep 10
}

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
		   #if PIDFILE PID is not running remove PIDFILE and start broker
		  rm -f ${PIDFILE}
          start_broker
		  fi
else
	#If PIDFILE missing start broker
   start_broker
fi

if [ -f ${PIDFILE_PREPROCESSOR} ] 
  then
      #if pidfile exists check the correct process is running
      kill -0 `cat ${PIDFILE_PREPROCESSOR}`
      RETVAL1=$?
      if [ ${RETVAL1} -eq 0 ]
        then
           #if valid PIDFILE content is running CS Preprocessor is UP 
           echo "CS Preprocessor Processes:        [RUNNING]" 
       else
           #if PIDFILE PID is not running remove PIDFILE and start preprocessor
          rm -f ${PIDFILE_PREPROCESSOR}
          start_preprocessor
          fi
else
    #If PIDFILE missing start broker
   start_preprocessor
fi

