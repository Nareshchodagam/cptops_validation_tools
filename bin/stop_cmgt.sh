#!/bin/bash
# $Id $

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

function stop_preprocessor {
su - csbroker -c "cd ${CMGT_PREPROCESSOR_ROOT}/cs_request_preprocessor && bin/cs_preprocessor.sh stop"
echo "CS Preprocessor Processes:        [STOPPED]"
}

function stop_broker {
su - csbroker -c "cd ${CMGT_ROOT}/cs_request_processor && bin/cs_processor.sh stop"
echo "CS Broker Processes:        [STOPPED]"
}

if [ -f ${PIDFILE} ] 
  then
	  #if pidfile exists stop CS Broker
	  stop_broker
else
   echo "ERROR CS Broker Processes:        [NOT RUNNING]"
fi

if [ -f ${PIDFILE_PREPROCESSOR} ] 
  then
      #if pidfile exists stop CS Preprocessor
      stop_preprocessor
else
   echo "ERROR CS Preprocessors Processes:        [NOT RUNNING]"
fi


