#!/bin/bash
#$Id: validate_splunkmgmt.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $

CHECK_PORT1=$(netstat -tulpn |grep -q 8089); RETVAL1=$?
CHECK_PORT2=$(netstat -tulpn |grep -q 8090); RETVAL2=$?
if [ ${RETVAL1} -eq 0 ] && [ ${RETVAL2} -eq 0 ]
        then
        echo "SPLUNKMGMT Processes:        [RUNNING]"
else
        echo "ERROR SPLUNKMGMT Processes:        [NOT RUNNING]"
        exit 1
fi
