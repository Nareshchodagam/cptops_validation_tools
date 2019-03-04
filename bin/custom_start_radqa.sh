#!/bin/bash

SLEEP=10

function action()
{
  while read MYH 
  do
    if [ $(hostname) == $MYH ]
    then
      cd /home/build/gro_testlink && source .env && /bin/docker-compose up -d
      echo "sleep for $SLEEP and check the service on $MYH ..."
      sleep $SLEEP
      curl $(hostname):8443 --noproxy $(hostname) 2>&1 1>/dev/null
      exit $?
    fi
  done
  echo "$(hostname) not part of cluster, nothing to do"
}

action << EOF
rd0-radqa1-1-prd.eng.sfdc.net
EOF
