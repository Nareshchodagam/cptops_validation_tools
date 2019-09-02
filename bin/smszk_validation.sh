#!/bin/bash

# Ensures that the zookeeper and zkHack systemd services are present and running

serviceQuery() {

  if systemctl list-units --full --all | grep -Fq ${1}; then
    echo "${1} is deployed. Checking status."

    if systemctl is-active --quiet ${1}; then
      echo "${1} is active."
    else
      echo "${1} is deployed but not active. Checking every 5 seconds for 1 minute before backing out"      
      for i in {1..12}
      do
        diff_time=$((60-$i*5))
        sleep 5

        if systemctl is-active --quiet ${1}; then
          echo "${1} is now active."
          break
        elif (( ${diff_time} > 0 )); then
          echo "${1} is still not active. ${diff_time} seconds remaining"
          continue
        else
          echo "${1} does not appear to be running. Please investigate and try again."
          exit 1
        fi

      done
    fi

  else
    echo "${1} is not installed on this host. Patching can continue"
    exit 0
  fi
}

serviceQuery zookeeper.service
serviceQuery zkHack.service
