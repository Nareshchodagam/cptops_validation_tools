#!/bin/bash

# Author: @wpiras@salesforce.com

su - csbroker -c "cd /home/csbroker/cs_api && bin/csapi.sh status"
RETVAL1=$?
if [ ${RETVAL1} -eq 0 ]
	then
		# If the previous script returned 0, CSApi is already running	
		echo "CSApi Processes:        [RUNNING]" 
	else
		# CSApi is not running
		echo "ERROR CSApi Processes:        [NOT RUNNING]" 
fi
