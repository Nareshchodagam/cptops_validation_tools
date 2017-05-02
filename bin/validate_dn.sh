#!/bin/bash
#$Id: validate_dn.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $
sleep 60
CHECK_MAPRED=$(ps -ef|grep -q [m]apred); RETVAL1=$?
CHECK_YARN=$(ps -ef|grep -q [y]arn); RETVAL2=$?
CHECK_HDFS=$(ps -ef|grep [h]dfs|grep -v yarn); RETVAL3=$?
CHECK_IMPALA=$(ps -ef|grep [i]mpala); RETVAL4=$?
CHECK_PORT=$(netstat -tulpn |grep -q 50010); RETVAL5=$?
if [ ${RETVAL1} -eq 0 ] && [ ${RETVAL2} -eq 0 ] && [ ${RETVAL3} -eq 0 ] && [ ${RETVAL4} -eq 0 ] && [ ${RETVAL5} -eq 0 ]
        then
        echo "DN Processes:        [RUNNING]"
else
        echo "ERROR DN Processes:        [NOT RUNNING]"
        exit 1
fi
