#!/bin/bash

CHECK_SVC=$(systemctl is-active --quiet secds); RETVAL=$?

if [ ${RETVAL} -eq 0 ]
        then
        echo "secds Processes:        [RUNNING]"
else
        echo "ERROR secds Processes:        [NOT RUNNING]"
        exit 1
fi
