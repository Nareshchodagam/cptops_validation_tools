#!/bin/bash
#
# Standardised script for validating systemd service status before and after patching
# Author: Aidan Steel (aidan.steel@salesforce.com)
#

USAGE="$(basename "$0") [-h] [-a] [-b]

Where:
  -h  show this help message and exit
  -a  perform pre-patching checks
  -b  perform post-patching checks

EXAMPLE: $(basename "$0") -a
"

# Role-specific services to be checked
services=(
  illumio-pce
)

serviceQuery() {
#
# Checks if service is deployed and running.
# If service deployed but not running, check at 5 second intervals for 1 minute
# If service still not running, attempt auto recovery
# If serviceQuery is being run as part of pre-patch checks, errors are collected but no auto recovery attempted
#
  if [[ -f "/etc/rc.d/init.d/${1}" ]]; then
    echo -e "\n${1} is deployed. Checking status"
    if systemctl is-active --quiet ${1}; then
      echo -e "${1} is active. \e[32mPatching can continue\e[0m"
    else
      echo -e "${1} is deployed but \e[31mnot active\e[0m\n"
      if [ "$STAGE" == 'pre-patch' ]; then
        pre_patch_errors+=(${1})
      else
        echo -e "Checking at 5 second intervals for 1 minute before attempting recovery\n"
        for i in {1..12}; do
          diff_time=$((60-$i*5))
          sleep 5
          if systemctl is-active --quiet ${1}; then
            echo -e "\n${1} is now active. \e[32mPatching can continue\e[0m"
            break
          elif (( ${diff_time} > 0 )); then
            echo "${1} is still not active. ${diff_time} seconds remaining"
            continue
          else
            echo -e "${1} is not active. \e[33mAttempting automatic recovery\e[0m\n"
            autoRecovery ${1}
          fi
        done
      fi
    fi
  else
    echo -e "${1} is not deployed on this host. \e[32mPatching can continue\e[0m"
    exit 0
  fi
}

autoRecovery() {
#
# Attempts to recover the service by running a systemctl restart
# Failed recovery attempts collected
#
  if systemctl restart ${1}; then
    sleep 5
    if systemctl is-active --quiet ${1}; then
      echo -e "${1} was successfully \e[32mrecovered\e[0m"
    else
      echo -e "\e[31mError\e[0m: Unable to recover ${1} through a service restart"
      post_patch_errors+=(${1})
    fi
  else
    echo -e "\n\e[31mError\e[0m: Failed to restart ${1}"
    post_patch_errors+=(${1})
  fi
}

runChecks() {
  if [ "$STAGE" == 'pre-patch' ]; then
    # Collect errors in this array to display at the end rather than failing on the first one
    pre_patch_errors=()
  elif [ "$STAGE" == 'post-patch' ]; then
    # Collect errors in this array to display at the end rather than failing on the first one
    post_patch_errors=()
  fi

  for service in "${services[@]}"; do
    serviceQuery $service
  done

  if [ $pre_patch_errors ]; then
    for broken_service in "${pre_patch_errors[@]}"; do
      echo -e "\e[31mError\e[0m: $broken_service is deployed but \e[31mnot active\e[0m"
    done
    echo -e "\nUntil the above errors are resolved, patching should not proceed"
    exit 1
  elif [ $post_patch_errors ]; then
    for broken_service in "${post_patch_errors[@]}"; do
      echo -e "\e[31mError\e[0m: Failed to recover $broken_service post patching"
    done
    echo -e "\nUntil the above errors are resolved, patching should not proceed"
    exit 1
  else
    echo -e "\nChecks completed \e[32msuccessfully\e[0m"
    exit 0
  fi
}

if (( $# != 1 )); then
  echo "This script must contain a single argument"
  exit 1
fi

while getopts ::hab option
  do
    case "${option}" in
      h) echo "$USAGE"
         exit ;;
      a) STAGE='pre-patch'
         runChecks ;;
      b) STAGE='post-patch'
         runChecks ;;
    esac
  done
