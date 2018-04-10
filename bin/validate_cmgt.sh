#!/bin/bash
#$Id: validate_cmgt.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $

####################################################################################
#
# Please contact the Certificate Service group for any info about this script
# https://gus.my.salesforce.com/0F9B00000006LcG
# 
# To test this script in the Cert Service DEV infrastructure just define CMGT_ROOT
# and CMGT_PREPROCESSOR_ROOT to point to the tested services instances. 
#
####################################################################################

CMGT_ROOT="/home/csbroker"
CMGT_PREPROCESSOR_ROOT="/home/csbroker"

PIDFILE="${CMGT_ROOT}/cs_request_processor-data/cs_request_processor.pid"
PIDFILE_PREPROCESSOR="${CMGT_PREPROCESSOR_ROOT}/cs_request_preprocessor-data/cs_request_preprocessor.pid"

# This service is active only in PHX, so we can use the DC proxy
export HTTPS_PROXY=https://public0-proxy1-0-phx.data.sfdc.net:8080/

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
           #if PIDFILE PID mismatch
          echo "ERROR CS Preprocessor Processes:        [WRONG PID FOUND]"
          fi
else
    #If PIDFILE missing
    echo "ERROR CS Preprocessors Processes:        [NOT RUNNING]"
fi

