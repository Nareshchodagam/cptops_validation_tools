#!/bin/bash
#$Id: validate_sfwupproxy.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $
sleep 60
CHECK_KAT=$(katello-service status|grep -q "Some services failed to status: qpidd"); RETVAL1=$?
if [ ${RETVAL1} -eq 0 ]
        then
        echo "Katello Processes:        [RUNNING]"
else
        echo "ERROR Katello Processes:        [NOT RUNNING]"
        exit 1
fi
