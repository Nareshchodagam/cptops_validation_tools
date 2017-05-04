#!/bin/bash
#$Id: validate_srdapp.sh 242488 2016-12-05 11:30:51Z iviscio@SFDC.NET $

sleep 60

if [ -f /opt/tarantella/bin/tarantella ]
  then
    STATUS=`/opt/tarantella/bin/tarantella status | grep $(hostname)|awk -F\: '{print $2}'`
    if [ "${STATUS}" == " Accepting secure connections." ]
      then
        echo "TARANTELLA :        [RUNNING]"
      else
        echo "ERROR TARANTELLA:        [NOT RUNNING]"
        exit 1
	fi
  else
     echo "Service Tarantella not installed"
fi
