#!/bin/bash
#$Id: validate_splunkidx.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $
sleep 40
CHECK_SPLUNK=$(ps -ef|grep "[s]plunkd -p 8089"); RETVAL1=$?
if [ ${RETVAL1} -eq 0 ]
        then
        echo "SPLUNK Processes:        [RUNNING]"
else
        echo "ERROR SPLUNK Processes:        [NOT RUNNING]"
        exit 1
fi

