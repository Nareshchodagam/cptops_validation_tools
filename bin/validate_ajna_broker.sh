#!/usr/bin/env bash
#
# Run this script at a kafka node as the effective
# user 'kafka'
#
# Arguments: [ verify | verifypost ]
#
#
# verify returns 0 if this node is suitable for patching

myname=$(basename "$0")

function underrepcheck() {
  su - kafka -c "source ajnarc; amiunderrep | grep -qw 0"
}

function verifypost() {
  underrepcheck
}

function verify() {
  underrepcheck
}


###########################################################

echo "Starting ${myname} ${1} at ${HOSTNAME} on $(date) ..."

if [[ "${USER}" != "root" ]] ; then
  echo "Script must be run as 'root' user, not ${USER} user"
  exit 1
fi

if [[ $1 == "verify" ]]; then
  verify
elif [[ $1 == "verifypost" ]]; then
  verifypost
else
  false
fi
rc=$?

echo "${myname} ${1} returning ${rc}"
exit ${rc}