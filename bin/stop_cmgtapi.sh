#!/bin/bash

# Author: @wpiras@salesforce.com

function stop_csapi {
	su - csbroker -c "cd /home/csbroker/cs_api && bin/csapi.sh stop"
	echo "CSApi Processes:        [STOPPED]"
}

su - csbroker -c "cd /home/csbroker/cs_api && bin/csapi.sh status"
RETVAL1=$?
if [ ${RETVAL1} -eq 1 ]
	then
		# If the previous script returned 1, CSApi was already stopped	
		echo "CSApi Processes:        [NOT RUNNING]" 
	else
		# If CSApi is running, stop it
		stop_csapi
fi