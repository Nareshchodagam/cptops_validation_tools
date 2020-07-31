#!/bin/bash
#
# csjenkins* roles use custom scripts under the jenkins home directory to manage their services rather than systemd
# Alterations to the standard format had to be made to accommodate this
# No autorecovery attempts to be made
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
  cs_processor
  cs_preprocessor
  cs_keymaker
)

serviceQuery() {
#
# Checks if service is deployed and running.
# Launches services in post-patch stage since these do not survive a reboot
# If service deployed but not running, check at 5 second intervals for 1 minute
# If service still not running, back out
#
  RUN_DIR=$(find /home/jenkins -name ${1}.sh -exec dirname {} \; 2> >(grep -v 'terminated by signal 13' >&2) | head -n 1 | sed 's,/*[^/]\+/*$,,')

  if [ $RUN_DIR ]; then
    # Services do not automatically start after reboot. Need to explicitly launch them before continuing
    if [ "$STAGE" == 'pre-patch' ]; then
      echo -e "\n${1} is deployed. Checking status"
      su jenkins -c "( cd $RUN_DIR && ./bin/${1}.sh status )"
      if [ $? -eq 0 ]; then
        echo -e "${1} is active. \e[32mPatching can continue\e[0m"
      else
        echo -e "${1} is deployed but \e[31mnot active\e[0m\n"
        pre_patch_errors+=(${1})
      fi
    elif [ "$STAGE" == 'post-patch' ]; then
      echo -e "\n${1} is deployed. Starting service and checking status"
      su jenkins -c "( cd $RUN_DIR && ./bin/${1}.sh start )"
      echo -e "Service started. Checking status at 5 second intervals for 1 minute before backing out\n"
      for i in {1..12}; do
        diff_time=$((60-$i*5))
        sleep 5
        su jenkins -c "( cd $RUN_DIR && ./bin/${1}.sh status )"
        if [ $? -eq 0 ]; then
          echo -e "\n${1} is now active. \e[32mPatching can continue\e[0m"
          break
        elif (( ${diff_time} > 0 )); then
          echo "${1} is still not active. ${diff_time} seconds remaining"
          continue
        else
          echo -e "\e[31mError\e[0m: ${1} is not active. Please contact the service owners\n"
          post_patch_errors+=(${1})
        fi
      done
    fi
  else
    echo -e "${1} is not deployed on this host. \e[32mPatching can continue\e[0m"
    exit 0
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
