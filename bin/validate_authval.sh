#!/bin/bash
# Validation script for Authval services
# Written by - Prerna Waghray & Syed Waheed
# FileName: validate_authval.sh

# Usage examples:
# ./remote_transfer/validate_authval.sh status
# ./remote_transfer/validate_authval.sh start
# ./remote_transfer/validate_authval.sh stop


# Release runner impl plan steps: (sample)
# For Status: release_runner.pl -forced_host hostname -c sudo_cmd -m "./remote_transfer/validate_authval.sh status" -threads -auto2 -property "sudo_cmd_line_trunk_fix=1" -comment 'BLOCK 5'
# For Start:  release_runner.pl -forced_host hostname -c sudo_cmd -m "./remote_transfer/validate_authval.sh start" -threads -auto2 -property "sudo_cmd_line_trunk_fix=1" -comment 'BLOCK 5'
# For Stop: release_runner.pl -forced_host hostname -c sudo_cmd -m "./remote_transfer/validate_authval.sh stop" -threads -auto2 -property "sudo_cmd_line_trunk_fix=1" -comment 'BLOCK 5'

SYSTEMCTL='/usr/bin/systemctl'

## Service Status
function status_postgresql () {
 $SYSTEMCTL is-active --quiet postgresql; if [ $? -eq 0 ]; then RETVAL_SQL=0; echo "POSTGRESQL:[RUNNING]"; else echo "POSTGRESQL:[NOT RUNNING]"; fi
}
function status_ksm () {
 $SYSTEMCTL is-active --quiet ksm; if [ $? -eq 0 ]; then RETVAL_KSM=0; echo "KSM:[RUNNING]"; else echo "KSM:[NOT RUNNING]"; fi
}
function status_val () {
 $SYSTEMCTL is-active --quiet val;if [ $? -eq 0 ]; then echo "VAL:[RUNNING]"; else echo "VAL:[NOT RUNNING]"; fi
}
#Use individual functions to check status of individual services.

## Start Services
function start_postgresql () {
$SYSTEMCTL is-active --quiet postgresql && RETVAL_SQL=0 && echo "POSTGRESQL:[ALREADY RUNNING]" && return 0 || RETVAL_SQL=1
if [ $RETVAL_SQL -ne 0 ]; then $SYSTEMCTL start postgresql && RETVAL_SQL=0 && echo "POSTGRESQL:[STARTED]"; 
elif [ $RETVAL_SQL == 1 ]; then  echo "Unable to start POSTGRESQL service" && exit 1; fi 
# IF STATUS_POSTGRESQL is NOT RUNNING then START POSTGRESQL service
}

function start_ksm () {
$SYSTEMCTL is-active --quiet ksm && RETVAL_KSM=0 && echo "KSM:[ALREADY RUNNING]" && return 0 || RETVAL_KSM=1
if [ $RETVAL_SQL == 0 ] && [ $RETVAL_KSM != 0 ]; then $SYSTEMCTL start ksm && RETVAL_KSM=0 && echo "KSM:[STARTED]"; 
elif [ $RETVAL_KSM == 1 ]; then echo "Unable to start KSM service" && exit 1; fi
# IF STATUS_POSTGRESQL is RUNNING & STATUS_KSM is NOT RUNNING then START KSM service
}

function start_val () {
$SYSTEMCTL is-active --quiet val && RETVAL_VAL=0 && echo "VAL:[ALREADY RUNNING]" && return 0 || RETVAL_VAL=1
if [ $RETVAL_SQL == 0 ] && [ $RETVAL_KSM == 0 ] && [ $RETVAL_VAL != 0 ]; then $SYSTEMCTL start val && echo "VAL:[STARTED]"; 
elif [ $RETVAL_VAL == 1 ]; then  echo "Unable to start VAL service" && exit 1; fi
# IF STATUS_POSTGRESQL is RUNNING & STATUS_VAL is NOT RUNNING then START VAL service
}

## Stop Services
function authval_stop () {
 echo "Please ensure that the AUTHRAD services are down on the same stack."  
 sleep 30
 $SYSTEMCTL stop val && echo "VAL:[STOPPED]" && sleep 2
 $SYSTEMCTL stop ksm && echo "KSM:[STOPPED]" && sleep 2
 $SYSTEMCTL stop postgresql && echo "POSTGRESQL:[STOPPED]" && sleep 2
}

## Service Status
function authval_status (){
 status_postgresql
 status_ksm
 status_val
}

## Start Services
function authval_start () {
 start_postgresql
 start_ksm
 start_val
}

## Main logic
if [ $# -eq 0 ] #if($# = 0) no. of arguments are zero, then print the help message.
then
 echo "Usage: $0 start|stop|status" && exit 1
else
 authval_$1 #$1 will take values as start|stop|status. example if $1 is status then it will execute function authrad_status.
fi

