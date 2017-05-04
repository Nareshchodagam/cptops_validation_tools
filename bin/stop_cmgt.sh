#!/bin/bash
# $Id $


PIDFILE="/home/csbroker/cs_request_processor-data/cs_request_processor.pid"

function stop_broker {
su - csbroker -c "cd /home/csbroker/cs_request_processor && bin/cs_processor stop"
echo "CS Broker Processes:        [STOPPED]"
}

if [ -f ${PIDFILE} ] 
  then
	  #if pidfile exists stop CS Broker
	  stop_broker
else
   echo "CS BROKER NOT RUNNING"
fi

