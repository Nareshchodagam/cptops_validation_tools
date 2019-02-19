#!/bin/bash
# Written by Funnel team (fka Ajna Ingestion)

AJNA_REST_STATUS="Not Running";
MANAGEMENT_PORT=15380

function getStatus {
    check=`curl "http://localhost:$MANAGEMENT_PORT/manage/health" 2>&1 | grep '"status" : "UP"' | wc -l`;

    if [[ "$check" -ne 0 ]]
    then
        AJNA_REST_STATUS="Running";
    fi
}

function status {
    getStatus;
    echo $AJNA_REST_STATUS;
    exitBasedOnStatus $AJNA_REST_STATUS;
}

function exitBasedOnStatus {
    if [ "$1" = "Running" ]
    then
        exit 0;
    else
        exit -1;
    fi
}

status

