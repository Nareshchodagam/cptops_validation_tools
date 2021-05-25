#!/bin/bash

# QuantumK service shutdown and verification
# Usage: quantumk_service.sh {stop|start|status}
# QuantumK is a keycloak based Security Token Service (STS) which runs on a 3 node cluster : quantumk1-1, 2-1 and 3-1
# Patching should be performed sequentially.
# Team contact quantumk@salesforce.com

containerUptime() {

  declare -a quantumk_containers
  quantumk_containers=(opt_health_1 opt_keycloak_1 opt_moria_1 opt_mariadb_1)
  # ALL CONTAINERS SHOULD BE UP FOR ATLEAST 3 MINS.
  acceptable_epoch_uptime=180

  sleep ${acceptable_epoch_uptime}
  current_epoch_time=$(date +'%s')
  for container in "${quantumk_containers[@]}"
    do
      container_epoch_uptime=$(docker inspect "${container}" --format='{{.State.StartedAt}}' | xargs -n1 date +%s -d)
      uptime=`expr "${current_epoch_time}" - "${container_epoch_uptime}"`
      # # factor in startup time.
      real_epoch_uptime=`expr "${acceptable_epoch_uptime}" - 60`
      if [ "${uptime}" -lt "${real_epoch_uptime}" ]
        then
	  echo "container ${container} not stable for the speficied time" && exit 1
      fi
    done
}

healthcheckQuery() {

if systemctl is-active --quiet docker.service && systemctl is-active --quiet quantumk.service; then

  HEALTHCHECK_PORT='8444'
  HEALTHCHECK_QUERY="http://localhost:${HEALTHCHECK_PORT}/health/status"

  curl -s ${HEALTHCHECK_QUERY} && HEALTH_RESPONSE=$(curl -s ${HEALTHCHECK_QUERY}) || exit 2
  echo ${HEALTH_RESPONSE} > /tmp/healthresponse.json 2>&1
  json_response=$(cat /tmp/healthresponse.json | \
    python -c 'import json,sys;obj=json.load(sys.stdin);print obj["realm_health_report_local"][0]["status"]');
  UPPER_RESPONSE=$(echo "${json_response^^}" | awk '{print $NF}')
  if [ "${UPPER_RESPONSE}" == "OK" ]
    then
      echo "Health check passed"
    else
      echo "fail" && exit 3
  fi
else
  echo "Check docker/quantumk.service" && exit 9
fi
}

case "$1" in
  stop)
    echo "Shutting down QuantumK"
    systemctl stop quantumk.service
    ;;
  status)
    containerUptime && healthcheckQuery
    ;;
  start)
    echo "Starting QuantumK"
    systemctl start quantumk.service
    $0 status
    ;;
  *)
    echo $"Usage: $0 {stop|start|status}"
esac

