#!/bin/bash
# Validation script for Authrad services
# Written by - Prerna Waghray & Syed Waheed
# FileName: validate_authrad.sh

# Usage Examples
# ./remote_transfer/validate_authrad.sh status
# ./remote_transfer/validate_authrad.sh start
# ./remote_transfer/validate_authrad.sh stop
# ./remote_transfer/validate_authrad.sh stackValidation

# Release runner implementation plan steps: (sample)
# For Status: release_runner.pl -forced_host hostname -c sudo_cmd -m "./remote_transfer/validate_authrad.sh status" -threads -auto2 -property "sudo_cmd_line_trunk_fix=1" -comment 'BLOCK 5'
# For Start:  release_runner.pl -forced_host hostname -c sudo_cmd -m "./remote_transfer/validate_authrad.sh start" -threads -auto2 -property "sudo_cmd_line_trunk_fix=1" -comment 'BLOCK 5'
# For Stop: release_runner.pl -forced_host hostname -c sudo_cmd -m "./remote_transfer/validate_authrad.sh stop" -threads -auto2 -property "sudo_cmd_line_trunk_fix=1" -comment 'BLOCK 5'
# For stackValidation: release_runner.pl -forced_host hostname -c sudo_cmd -m "./remote_transfer/validate_authrad.sh stackValidation" -threads -auto2 -property "sudo_cmd_line_trunk_fix=1" -comment 'BLOCK 5'

HOSTNAME=`uname -n | cut -d "." -f1`
SYSTEMCTL='/usr/bin/systemctl'

## Service Status
function status_postgresql () {
  $SYSTEMCTL is-active --quiet postgresql;if [ $? -eq 0 ]; then RETVAL_SQL=0 && echo "POSTGRESQL:[RUNNING]"; else echo "POSTGRESQL:[NOT RUNNING]"; fi
}
function status_radiusd () {
  $SYSTEMCTL is-active --quiet radiusd;if [ $? -eq 0 ]; then RETVAL_RAD=0 && echo "RADIUSD:[RUNNING]"; else echo "RADIUSD:[NOT RUNNING]"; fi
}
function status_authradiant () {
  $SYSTEMCTL is-active --quiet authradiant;if [ $? -eq 0 ]; then echo "AUTHRADIANT:[RUNNING]"; else echo "AUTHRADIANT:[NOT RUNNING]"; fi
}
#Use individual functions to check status of individual services.

## Start Services
function start_postgresql () {
$SYSTEMCTL is-active --quiet postgresql && RETVAL_SQL=0 && echo "POSTGRESQL:[ALREADY RUNNING]" && return 0 || RETVAL_SQL=1
if [ $RETVAL_SQL -ne 0 ]; then $SYSTEMCTL start postgresql && RETVAL_SQL=0 && echo "POSTGRESQL:[STARTED]"; 
elif [ $RETVAL_SQL == 1 ]; then  echo "Unable to start POSTGRESQL service" && exit 1; fi 
# IF STATUS_POSTGRESQL is NOT RUNNING then START POSTGRESQL service
}

function start_radiusd () {
$SYSTEMCTL is-active --quiet radiusd && RETVAL_RAD=0 && echo "RADIUSD:[ALREADY RUNNING]" && return 0 || RETVAL_RAD=1
if [ $RETVAL_SQL == 0 ] && [ $RETVAL_RAD != 0 ]; then $SYSTEMCTL start radiusd && RETVAL_RAD=0 && echo "RADIUSD:[STARTED]"; 
elif [ $RETVAL_RAD == 1 ]; then  echo "Unable to start RADIUSD service" && exit 1; fi
# IF STATUS_POSTGRESQL is RUNNING & STATUS_RADIUSD is NOT RUNNING then START RADIUSD service
}

function start_authradiant () {
$SYSTEMCTL is-active --quiet authradiant && RETVAL_RADIANT=0 && echo "AUTHRADIANT:[ALREADY RUNNING]" && return 0 || RETVAL_RADIANT=1
if [ $RETVAL_SQL == 0 ] && [ $RETVAL_RAD == 0 ] && [ $RETVAL_RADIANT != 0 ]; then $SYSTEMCTL start authradiant && echo "AUTHRADIANT:[STARTED]"; 
elif [ $RETVAL_RADIANT == 1 ]; then  echo "Unable to start AUTHRADIANT service" && exit 1; fi
# IF STATUS_POSTGRESQL is RUNNING & STATUS_RADIUSD is NOT RUNNING then START AUTHRADIANT service
}

function authrad_stackValidation () {
 echo "Authradiant takes a minimum of 60 seconds to do the first health check after it is restarted" 
 sleep 60
 #checking last few lines and also the status of AuthRadiant
 if  `$SYSTEMCTL is-active --quiet authradiant` && `journalctl -u authradiant |tail -n 5 | grep -q 'Healthcheck successful'` ; then
    echo "$HOSTNAME: Health check successful, next host can be patched"
 else
    echo "$HOSTNAME: Health check failed, do not patch the next host until healthcheck succeeds"
    exit 1
 fi
}


## Stop Services
function authrad_stop () {
  $SYSTEMCTL stop authradiant && sleep 2 && echo "AUTHRADIANT:[STOPPED]"
  $SYSTEMCTL stop radiusd && sleep 2 && echo "RADIUSD:[STOPPED]"
  $SYSTEMCTL stop postgresql && sleep 2 && echo "POSTGRESQL:[STOPPED]"
}

## Service Status
function authrad_status (){
  status_postgresql
  status_radiusd
  status_authradiant
}

## Start Services
function authrad_start () {
  start_postgresql
  start_radiusd
  start_authradiant
}


## Main logic
if [  $# -eq 0 ] #if no. of arguments are zero, then print the help message.
then
  echo "Usage: $0 start|stop|status|stackValidation" && exit 1
else
  authrad_$1   #$1 will take values as start|stop|status|stackValidation. example if $1 is status then it will execute function authrad_status.
fi

