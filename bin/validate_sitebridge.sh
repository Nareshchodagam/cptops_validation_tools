#!/bin/env bash

# Sitebridge service validation script
# Cillian Gallagher 01Nov18
# Chris Woodfield 29Mar19

CONTAINERD_CONFIG_PATH_DEPRECATED="/var/run/docker"
CONTAINERD_CONFIG_PATH_NEW="/etc/containerd"
CONTAINERD_CONFIG_FILE="containerd.toml"
CONTAINERD_FILE_TEXT=$(cat <<EOF
root = "/cowdata/docker/containerd/daemon"
state = "/var/run/docker/containerd/daemon"
oom_score = -500
disabled_plugins = ["cri"]

[grpc]
  address = "/var/run/docker/containerd/docker-containerd.sock"
  uid = 0
  gid = 0
  max_recv_message_size = 16777216
  max_send_message_size = 16777216

[debug]
  address = "/var/run/docker/containerd/docker-containerd-debug.sock"
  uid = 0
  gid = 0
  level = "info"

[metrics]
  address = ""
  grpc_histogram = false

[cgroup]
  path = ""

[plugins]
  [plugins.linux]
    shim = "docker-containerd-shim"
    runtime = "docker-runc"
    runtime_root = "/cowdata/docker/runc"
    no_shim = false
    shim_debug = false\n
EOF
)

BOOTSTRAPPER_SVCNAME="sitebridge-bootstrapper"
SYSTEMCTL_CMD="/bin/systemctl"
SYSTEMCTL_BOOTSTRAPPER_START_CMD="${SYSTEMCTL_CMD} start ${BOOTSTRAPPER_SVCNAME}"
DOCKER_CMD="/usr/bin/docker"
SYSTEMCTL_DOCKER_START_CMD="${SYSTEMCTL_CMD} start docker"
VALIDATION_WAIT_TIME=180
CPT_VALIDATOR_CMD="/sitebridge/sitebridge-cpt-validator"
# Checks the existing bootstrapper image for TnRP vs Strata image.
DOCKER_OLD_BOOTSTRAPPER_CMD="${DOCKER_CMD} ps --filter='name=${BOOTSTRAPPER_SVCNAME}' --format='{{ .Image }}' | cut -d: -f2 | grep -q -E '^v-.*\$'; echo \$?"
SYSTEMCTL_IS_ACTIVE_CMD="${SYSTEMCTL_CMD} is-active -q"


# First check if containerd config file exists. Restore it if not
# In both locations; we can deprecate /var/run once we've deployed our fix.

if [[ ! -f ${CONTAINERD_CONFIG_PATH_DEPRECATED}/${CONTAINERD_CONFIG_FILE} && \
  ! -f ${CONTAINERD_CONFIG_PATH_NEW}/${CONTAINERD_CONFIG_FILE} ]]; then
    echo "${CONTAINERD_CONFIG_FILE} not found, restoring..."

    if [[ ! -d ${CONTAINERD_CONFIG_PATH_DEPRECATED} ]]; then
        mkdir -p ${CONTAINERD_CONFIG_PATH_DEPRECATED}
        chown root:root ${CONTAINERD_CONFIG_PATH_DEPRECATED}
        chmod 755 ${CONTAINERD_CONFIG_PATH_DEPRECATED}
    fi
    echo -e "${CONTAINERD_FILE_TEXT}" > ${CONTAINERD_CONFIG_PATH_DEPRECATED}/${CONTAINERD_CONFIG_FILE}

    # Start bootstrapper
    echo "Starting up ${BOOTSTRAPPER_SVCNAME}..."
    ${SYSTEMCTL_BOOTSTRAPPER_START_CMD}
    echo "Sleeping for ${VALIDATION_WAIT_TIME}s before validating sitebridge components."
    sleep ${VALIDATION_WAIT_TIME}
fi

# Check for older version of sitebridge-bootstrapper, run simple service check if we don't have
# a version running the new validator. Since all current builds are on Strata, this is easy to check.
# (eval is needed so that pipe chars don't get interpreted as command args)
check_old_rev=`eval "${DOCKER_OLD_BOOTSTRAPPER_CMD}"`
if [[ ${check_old_rev} == 0 ]]; then
    echo "Found older revision of sitebridge-bootstrapper, falling back to basic check"
    check_bootstrapper_svc=`${SYSTEMCTL_CMD} is-active -q ${BOOTSTRAPPER_SVCNAME}; echo $?`
    if [[ ${check_bootstrapper_svc} == 0 ]]; then
        echo "Sitebridge Processes:              [RUNNING]"
        exit 0
    else
        echo "ERROR Sitebridge Processes:        [NOT RUNNING]"
        exit 1
    fi
fi

check_svc_cmd="${DOCKER_CMD} exec ${BOOTSTRAPPER_SVCNAME} ${CPT_VALIDATOR_CMD}"
check_svc=`${check_svc_cmd}; echo $?`
if [[ "${check_svc}" == 0 ]]; then
    echo "Sitebridge Processes:              [RUNNING]"
    exit 0
else
    echo "ERROR Sitebridge Processes:        [NOT RUNNING]"
    exit 1
fi
