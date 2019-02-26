#!/bin/bash
# Written by Funnel team (fka Ajna Ingestion)

AJNA_REST_STATUS="Not Running";
PROP_FILE=/home/sfdc-ajnaep/current/ajna-rest-endpoint/ajna-rest-endpoint/config/application.properties
if [ ! -f "$PROP_FILE" ]; then
	echo "$PROP_FILE doesn't exist"
	exit -1;
fi


MANAGEMENT_PORT=`grep -m 1 '^management.server.port=' $PROP_FILE | cut -d'=' -f2`

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
        exit 3;
    fi
}

status
