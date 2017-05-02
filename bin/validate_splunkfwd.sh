#!/bin/bash
#$Id: validate_splunkfwd.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $
sleep 40
CHECK_SPLUNK=$(ps -ef|grep -q "[f]lume\|[r]syslogd"); RETVAL1=$?
if [ ${RETVAL1} -eq 0 ]
        then
        echo "FLUME and RSYSLOGD Processes:        [RUNNING]"
else
        echo "ERROR FLUME and RSYSLOGD  Processes:        [NOT RUNNING]"
        exit 1
fi

