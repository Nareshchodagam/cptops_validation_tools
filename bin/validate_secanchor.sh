#!/bin/bash
#$Id: validate_secanchor.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $

CHECK_K2K=$(ps -ef|grep -q [k]2k); RETVAL1=$?
CHECK_SPLUNK=$(ps -ef|grep -q [s]plunkd); RETVAL2=$?
if [ ${RETVAL1} -eq 0 ] && [ ${RETVAL2} -eq 0 ]
        then
        echo "K2K-SPLUNK Processes:        [RUNNING]"
else
        echo "ERROR K2K-SPLUNK Processes:        [NOT RUNNING]"
        exit 1
fi
