#!/bin/bash

CHECK_SVC=$(systemctl is-active --quiet seciamsvc); RETVAL=$?

if [ ${RETVAL} -eq 0 ]
        then
        echo "seciamsvc Processes:        [RUNNING]"
else
        echo "ERROR seciamsvc Processes:        [NOT RUNNING]"
        exit 1
fi
