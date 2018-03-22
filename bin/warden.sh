#!/bin/bash
#
# This script is used to start/stop service for the Warden roles.
#

function warden_app {
CMD_NAME='$HOME/start-stop.sh'
su - sfdc -c "$CMD_NAME $CMD"
if [ $? -eq 0 ]
then
    echo "Succesfully completed $CMD of application."
    exit 0
else
    echo "Failed to $CMD application."
    exit 1
fi
}

function warden_mq {
if [ $CMD == "start" ]
then
    su - sfdc -c 'source $HOME/warden.rc ; nohup $KAFKA_HOME/bin/kafka-server-start.sh $KAFKA_HOME/config/server.properties > $KAFKA_HOME/kafka.log 2> $KAFKA_HOME/Error.err < /dev/null &'
    sleep 5
    PID=`ps -ef | grep kafka | grep sfdc | awk '{print $1}'`seq 88-9
    if [ $PID == "sfdc" ]
    then
        ret_code=0
    else
        ret_code=1
    fi
    error_check
else
    su - sfdc -c 'source $HOME/warden.rc ; nohup $KAFKA_HOME/bin/kafka-server-stop.sh $KAFKA_HOME/config/server.properties > $KAFKA_HOME/kafka.log 2> $KAFKA_HOME/Error.err < /dev/null &'
    sleep 5
    PID=`ps -ef | grep kafka | grep sfdc| awk '{print $1}'`
    if [ -z $PID ]
    then
        ret_code=0
    else
        ret_code=1
    fi
    error_check
fi
}

function warden_ws {
if [ $CMD == "start" ];
then
    su - sfdc -c 'source $HOME/warden/warden.rc ; $TOMCAT_HOME/bin/startup.sh'
    ret_code=$?
    error_check
else
    su - sfdc -c '$HOME/warden/tomcat/bin/shutdown.sh'
    ret_code=$?
    error_check
fi
}

function error_check {
if [ $ret_code == 0 ]
then
    echo "Command executed successfully"
    exit 0
else
    echo "Command failed."
    exit 1
fi
}

#Main
#####################################
if [ $# -ne 2 ]
then
    echo "Usage $0 role_name start|stop"
    exit 1
else
    ROLE="$1"
    CMD="$2"
fi

if [ "$CMD" == "start" ] || [ "$CMD" == "stop" ]
then
    if [ "$ROLE" == "warden_prod_alert" ] || [ "$ROLE" == "warden_prod_writed" ] || [ "$ROLE" == "warden_prod_readd" ]
    then
        warden_app $CMD
    elif [ "$ROLE" == "warden_prod_mq" ]
    then
        warden_mq $CMD
    elif [ "$ROLE" == "warden_prod_ws" ]
    then
        warden_ws $CMD
    else
        echo "Role not listed - Nothing to start/stop"
        exit 0
    fi
else
    echo "Usage $0 role_name start|stop"
    exit 1
fi