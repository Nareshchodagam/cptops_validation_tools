#!/bin/bash
#
# This script is used to start/stop service for the Warden roles.
#

function warden_writed {
su - sfdc -c "$HOME/start-stop.sh $CMD"
if [ $? -eq 0 ]
then
    echo "Succesfully started app."
    exit 0
else
    echo "Failed to start app."
    exit 1
fi
}


function warden_mq {
if [ $CMD == "start" ]
then
    su - sfdc -c "source $HOME/warden.rc ; startkafka"
    ret_code = $?
else
    su - sfdc -c "source $HOME/warden.rc ; stopkafka"
    ret_code = $?
fi
}


function warden_ws {
if [ $CMD == "start" ];
then
    su - sfdc -c "source $HOME/warden/warden.rc ; starttomcat"
    ret_code = $?
else
    su - sfdc -c "source $HOME/warden/warden.rc ; starttomcat"
    ret_code = $?
fi

}
function test {
if [ $CMD == "start" ];
then
    source /tmp/warden.rc
    echo $var
    ret_code="$?"
else
    su - sfdc -c "source /tmp/warden.rc ; echo $var"
    ret_code = $?
fi

}

function error_check {
if [ ret_code -eq 0 ]
then
    echo "Command executed successfully"
    exit 0
else
    echo "Command failed."
    exit 1
fi
}


#Main
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
        echo "warden_writed $*"
    elif [ "$ROLE" == "warden_prod_mq" ]
    then
        echo "next"
    elif [ "$ROLE" == "test" ]
    then
        echo $var
        test $CMD
    fi
else
    echo "Usage $0 role_name start|stop"
    exit 1
fi