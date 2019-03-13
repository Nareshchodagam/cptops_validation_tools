#!/bin/bash
# Sitebridge service validation script
# Cillian Gallagher 01Nov18
# Chris Woodfield 24Feb19

CONTAINERD_CONFIG_PATH_DEPRECATED="/var/run/docker"
CONTAINERD_CONFIG_PATH_NEW="/etc/containerd"
CONTAINERD_CONFIG_FILE="containerd.toml"
PUPPET_CMD="/bin/puppet agent -t"
BOOTSTRAPPER_SVCNAME="sitebridge-bootstrapper"
SYSTEMCTL_CMD="/bin/systemctl"
SYSTEMCTL_START_CMD="${SYSTEMCTL_CMD} start ${BOOTSTRAPPER_SVCNAME}"
DOCKER_CMD="/usr/bin/docker"
CPT_VALIDATOR_CMD="/sitebridge/sitebridge-cpt-validator"

# First check if containerd config file exists. Run puppet to restore it if not
if [ ! -f ${CONTAINERD_CONFIG_PATH_DEPRECATED}/${CONTAINERD_CONFIG_FILE} ] && \
  [ ! -f ${CONTAINERD_CONFIG_PATH_NEW}/${CONTAINERD_CONFIG_FILE} ]
then
    echo "${CONTAINERD_CONFIG_FILE} not found, running puppet to restore..."
    ${PUPPET_CMD}; puppet_retval=$?
    if [ ${puppet_retval} -ne 0 ]
    then
      echo "Puppet run failed, exiting"
      exit 1
    fi

    # Bootstrapper should be able to run now
    ${SYSTEMCTL_START_CMD}
    # Give components an opportunity to start up
    sleep 60
fi

check_svc_cmd="${DOCKER_CMD} exec ${BOOTSTRAPPER_SVCNAME} ${CPT_VALIDATOR_CMD}"
check_svc=`${check_svc_cmd}; echo $?`
if [ "${check_svc}" == 0 ]
        then
        echo "Sitebridge Processes:              [RUNNING]"
else
        echo "ERROR Sitebridge Processes:        [NOT RUNNING]"
        exit 1
fi
