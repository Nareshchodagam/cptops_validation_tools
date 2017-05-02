#!/bin/bash
#$Id: validate_splunksrh.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $

CHECK_PORT1=$(netstat -tulpn |grep -q 8090); RETVAL1=$?
if [ ${RETVAL1} -eq 0 ]
        then
        echo "SPLUNKSRH Processes:        [RUNNING]"
else
        echo "ERROR SPLUNKSRH Processes:        [NOT RUNNING]"
        exit 1
fi
