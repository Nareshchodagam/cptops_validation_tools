#!/usr/bin/env bash
#
#
# Assign variables
start_cmd=`rpm -ql RdbmsServiceRPM | grep "/start.sh"`
stop_cmd=`rpm -ql RdbmsServiceRPM | grep "/stop.sh"`
status_cmd=`rpm -ql RdbmsServiceRPM | grep "/isrunning.sh"`


function status {
    echo "Checking Broker status"
    su - sfdc-dbaas -c "bash $status_cmd"
}

function start_broker {
    echo "Starting Broker application"
    su - sfdc-dbaas -c  "bash $start_cmd"
}

function stop_broker {
    echo "Stopping Broker application"
    su - sfdc-dbaas -c  "bash $stop_cmd"
}


case "$1" in
    start)
        start_broker
        ;;
    stop)
        stop_broker
        ;;
    status)
        status
        ;;
    *)
        echo "./dbaas_broker.sh <start|stop|status>"
        ;;
    esac
