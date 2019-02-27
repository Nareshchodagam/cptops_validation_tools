#!/bin/bash

ACTIVITY=0
while read MYC
do
  echo "attempting to stop $MYC container"
  (cd /home/build/gro && /bin/docker-compose stop $MYC) 2>&1 
  if [ $? != 0 ]
  then
    echo "failed to stop $MYC container"
    exit 1
  fi
  let ACTIVITY=ACTIVITY+1
done < <( curl --unix-socket /var/run/docker.sock http:/v1.24/containers/json 2>/dev/null \
| /usr/bin/python -c "import sys, json; [sys.stdout.write(rec['Names'][0][1:] + '\n') for rec in json.load(sys.stdin)]" \
| cut -d_ -f2 )

if [ $ACTIVITY -eq 0 ]
then
  echo "no containers found to stop on host $(hostname)"
fi
