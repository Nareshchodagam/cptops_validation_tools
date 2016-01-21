#!/bin/bash

PATH='/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin'
umask 022

HERMES_CONFIG_FILE='/'
#CONFIG_ROOTS='/home/sfdc /home/vagrant/blt' #TODO -- Confirm this is right
#CONFIG_PATH='apps/liveagent/main/messagingservice/config'
#CONFIG_FILE='messaging-*.config'
FULL_PATH=''

ACTION='create'

# Functions used later

list_loopback_ifs () {
  ifconfig -a | grep '^lo:[0-9]' | awk '{print $1}'
}

display_current_rules () {
  iptables -t nat -L -n 2>&1 | grep -E -- "\s[0-9.]*\s*tcp\s*dpt:10004\s*to:127\.0\.0\.1:10005"
}

display_current_rules_removed () {
  iptables -t nat -L -n 2>&1 | grep -E -- "\s[0-9.]*\s*tcp\s*dpt:10004\s*to:127\.0\.0\.1:10005"
  if [[ $? -eq 1 ]]
  then
  	return 0
  fi
}

create_iptables_rule () {
  local IP="$1"

  iptables -t nat -L -n 2>/dev/null | grep -Eq -- "\s${IP//./\\.}\s*tcp\s*dpt:10004\s*to:127\.0\.0\.1:10005"
  if [[ $? -eq 0 ]]
  then
    # The rule already exists
    echo "The ip [${IP}] already has an iptables rule. Skipping..." >&2
    return 0
  fi

  # Create the iptables rule
  iptables -t nat -A OUTPUT -p tcp -d ${IP} --dport 10004 -j DNAT --to 127.0.0.1:10005
  return $?
}

delete_iptables_rule () {
  local IP="$1"
  iptables -t nat -L -n 2>/dev/null | grep -Eq -- "\s${IP//./\\.}\s*tcp\s*dpt:10004\s*to:127\.0\.0\.1:10005"
  if [[ $? -ne 0 ]]
  then
    # The rule does not exist
    echo "The rule for ip [${IP}] can't be found. Error..." >&2
    echo "Here are the only rules I see:" >&2
    display_current_rules >&2
    return 1
  fi

  # Delete the rule
  iptables -t nat -D OUTPUT -p tcp -d ${IP} --dport 10004 -j DNAT --to 127.0.0.1:10005
  return $?
}

#create_if () {
#  local IP="$1"
#  local loopback_ifs=$(list_loopback_ifs)
#
#  # First, if the IP address is already configured on a virtual loopback, just
#  # exit cleanly.
#  local my_if
#  for my_if in ${loopback_ifs}
#  do
#    ifconfig "${my_if}" | grep -q "${IP//./\\.}" && return 0
#  done
#
#  # Determine the number of the next virtual loopback interface
#  local NEXT_IFNO=0
#  for my_if in ${loopback_ifs}
#  do
#    local my_ifno="${my_if#*:}"
#    # Make sure that the interface we are looking at is a virtual interface
#    # (i.e. it ends with ":[0-9]":
#    echo "${my_ifno}" | grep -q '^[0-9][0-9]*$' || continue
#
#    if [[ ${my_ifno} -ge ${NEXT_IFNO} ]]
#    then
#      NEXT_IFNO=$((my_ifno + 1))
#    fi
#  done
#
#  local MY_VIRT_IF="lo:${NEXT_IFNO}"
#
#  # This command brings up the virtual interface:
#  ifconfig "${MY_VIRT_IF}" "${IP}" netmask 255.255.255.255
#
#  # This next stuff creates the startup file so it will come up at next boot
#  local IF_FILE="/etc/sysconfig/network-scripts/ifcfg-${MY_VIRT_IF}"
#  if [[ -e ${IF_FILE} ]]
#  then
#    echo "Interface config file [${IF_FILE}] already exists! ERROR" >&2
#    return 1
#  fi
#  touch ${IF_FILE}
#  chmod 644 ${IF_FILE} ##TODO(mpettit) -- Investigate this
#  chown root:root ${IF_FILE} ##TODO(mpettit) -- Investigate this
#  cat >${IF_FILE} <<EOF
#DEVICE=${MY_VIRT_IF}
#IPADDR=${IP}
#NETMASK=255.255.255.255
#BOOTPROTO=none
#ONBOOT=yes
#EOF
#
#  # All done!
#  return 0
#}

#delete_if () {
#  local IP="$1"
#  local loopback_ifs=$(list_loopback_ifs)
#
#  # First, find the interface where the IP currently lives
#  local my_if
#  for my_if in ${loopback_ifs}
#  do
#    local my_ifno="${my_if#*:}"
#    # Make sure that the interface we are looking at is a virtual interface
#    # (i.e. it ends with ":[0-9]":
#    echo "${my_ifno}" | grep -q '^[0-9][0-9]*$' || continue
#
#    ifconfig "${my_if}" | grep -q "addr:${IP//./\\.} "
#    if [[ $? -eq 0 ]]
#    then
#      # Found the correct interface to delete
#      ifconfig "${my_if}" down
#      rm -f "/etc/sysconfig/network-scripts/ifcfg-${my_if}"
#      return 0
#    fi
#  done
#
#  # If execution falls through to here, we were not able to find the IP.
#  echo "Unable to find IP [${IP}] on any loopback interface" >&2
#  return 1
#}

help () {
  cat >&2 <<EOF
Usage: $0 [-dh] -f config_file host1 { host2 { ... } }

    The following options are available:

    -d    Delete an interface instead of creating one.

    -f    Full path to the Hermes config file

    -h    Print this help and exit.

    This script is used to create (or delete) virtual loopback interfaces
    (lo:0, lo:1, etc.) to assist the Hermes peer-detection protocol from
    failing when a host has actually physically died (gone offline). The
    intention is that this script will be run on all remaining Hermes nodes,
    with the hostname of the "down" host.

    This can also be done to intentionally remove some nodes for maintenance.
    Simply run the script on all "live" servers, giving the list of all nodes
    to be removed. Then the "down" servers may be rebooted / upgraded /
    whatever is needed.

    If the "-d" argument is given, the virtual interface is *removed*, not
    created. This is intended for after the maintenance, or after the host has
    come back up.
EOF
}

# Make sure we're running as root.

if [[ $EUID != 0 ]]
then
  echo 'This must be run as root.' >&2
  exit 1
fi

# Setup: What action will we be performing?

while getopts dhf: opt
do
  case $opt in
  d)
    ACTION='delete'
    ;;
  h)
    help
    exit 0
    ;;
  f)
    HERMES_CONFIG_FILE="${OPTARG}"
    ;;
  *)
    echo "Invalid option or missing argument: -$opt"
    exit 1
    ;;
  esac
done

shift $((OPTIND - 1))

# PEERS is an array containing hostnames for which we will be either
# creating or deleting virtual loopback addresses.
declare -a PEERS=("$@")
declare -a PEER_IPS=()

# Step 1 & 2 are gone now -- Instead you must specify the config file with -f.

if [[ ! -f ${HERMES_CONFIG_FILE} ]]
then
  echo "Unable to find Hermes config file at [${HERMES_CONFIG_FILE}]" >&2
  exit 1
fi

# Step 3: Determine the full list of peers

# Initially, the config line looks like this:
# service.replicationcluster.addresses=hostA:portA;hostB:portB;hostC:portC
HERMES_PEERS=$(grep '^service\.replicationcluster\.addresses=' "${HERMES_CONFIG_FILE}" | sed -E -e 's/^[^=]*=//' -e 's/;/ /g' -e 's/:[0-9]*//g')
# After filtering & munging, HERMES_PEERS now has: 'hostA hostB ...'

# Step 4: Validate the input hostnames against the list of peers -- exit
# if any mismatch is found.

for HOST in "${PEERS[@]}"
do
  # Skip this check if $HOST is an IP address.
  if [ $(expr "$HOST" : '[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*$') -gt 0 ]
  then
    PEER_IPS+=("${HOST}")
    continue
  fi
  VALID_HOST=0
  for HERMES_HOST in ${HERMES_PEERS}
  do
    if [[ ${HOST} == ${HERMES_HOST} ]]
    then
      VALID_HOST=1
      break
    fi
  done
  if [[ ${VALID_HOST} -ne 1 ]]
  then
    echo "[${HOST}] is not a valid Hermes host." >&2
    exit 1
  fi

  HOST_IP=$(host -t a "${HOST}" | grep 'has address' | head -1 | awk '{print $NF}')
  # Make sure that the hostname resolves to an IP:
  if [ $(expr "${HOST_IP}" : '[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*$') -eq 0 ]
  then
    echo "Unable to resolve [${HOST}]." >&2
    exit 1
  fi
  PEER_IPS+=("${HOST_IP}")
done

# Step 5: For each requested host, perform the requested action
#
# If the action is "create", we need to create a iptables rule for the IP of
# the peer. If the action is "delete", delete the iptables rule.

for IP in "${PEER_IPS[@]}"
do
  if [[ ${ACTION} == 'create' ]]
  then
    create_iptables_rule "${IP}"
    if [[ $? -ne 0 ]]
    then
      echo "I had a problem creating [${IP}] -- Manual intervention needed" >&2
      exit 1
    fi
  elif [[ ${ACTION} == 'delete' ]]
  then
    delete_iptables_rule "${IP}"
    if [[ $? -ne 0 ]]
    then
      echo "I had a problem deleting [${IP}] -- Manual intervention needed" >&2
      exit 1
    fi
  else
    echo "Unexpected error: Unrecognized action [${ACTION}]" >&2
    exit 1
  fi
done

# All done. Output a summary of what was done.

if [[ ${ACTION} == 'create' ]]
then
  echo 'All rules added. Current state:'
  display_current_rules
else
  echo 'All rules removed. Current state:'
  display_current_rules_removed
fi