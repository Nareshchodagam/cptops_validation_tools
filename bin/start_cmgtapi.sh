#!/bin/bash

# Author: @wpiras@salesforce.com

sleep 30

function start_csapi {
	su - csbroker -c "cd /home/csbroker/cs_api && bin/csapi.sh start"
	echo "CSApi Processes:        [STARTED]"
}

su - csbroker -c "cd /home/csbroker/cs_api && bin/csapi.sh status"
RETVAL1=$?
if [ ${RETVAL1} -eq 0 ]
	then
		# If the previous script returned 0, CSApi is already running	
		echo "CSApi Processes:        [RUNNING]" 
	else
		# If CSApi is not running, start it
		start_csapi
fi