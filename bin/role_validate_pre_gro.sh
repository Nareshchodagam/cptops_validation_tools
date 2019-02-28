#! /bin/bash

HEALTHY=0
function checkHealth()
{
  RAWHOST_FQDN=$1
  curl $RAWHOST_FQDN:3000 --noproxy $RAWHOST_FQDN 2>&1 1>/dev/null
  return $?
}


function action()
{
  while read MYH; do
    if [ "$MYH" != "$(hostname)" ] #we do not count health of current host for precheck so skip
    then
      checkHealth $MYH
      if [ $? -eq 0 ]
      then
        let HEALTHY=HEALTHY+1
      fi
    fi
  done
  echo "Cluster has $HEALTHY healthy hosts (current host $(hostname) is not checked)"
  exit $(test $HEALTHY -gt 0)
}

action << EOF
rd0-gro1-1-prd.eng.sfdc.net
rd0-gro1-2-prd.eng.sfdc.net
EOF
