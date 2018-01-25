#!/bin/bash
# script to disable perm killing ibrs and ibpb fixes in the meltdown/spectre
# kernel updates.  Maintains PTI setting
# only applicable to hosts patched using the 2018.0104 bundle
# will also run against 2018.0117, but should just be no-op - settings
# should already be correct on that version.
# Jason O'Rourke - Jan 19 2018

function orb_bundle_check
{
  bundle_version=`rpm -q --queryformat '%{VERSION}' sfdc-release`
  if [[ $bundle_version = '2018.0104' || $bundle_version = '2018.0117' ]]; then
    echo "M/S Bundle $bundle_version present on $HOSTNAME"
  else
    echo "$HOSTNAME not running relevant bundle.  Nothing to do."
  exit 0
  fi
}

function debug_mount
# Centos6 hosts likely will not have /sys/kernel/debug mounted
{
  if ! grep -Fq /sys/kernel/debug /etc/mtab ; then
    echo "mounting debugfs on /sys/kernel/debug"
    /bin/mount -t debugfs nodev /sys/kernel/debug
  fi
}


function flag_check
{
  if [ -d /sys/kernel/debug/x86 ]; then
    if [ `cat /sys/kernel/debug/x86/ibrs_enabled` = 1 ]; then
      echo "IBRS enabled - NEEDS to be disabled"
      fix_ibrs=true
    else
      echo "IBRS disabled - CORRECT setting"
      fix_ibrs=false
    fi

    if [ `cat /sys/kernel/debug/x86/ibpb_enabled` = 1 ]; then
      echo "IBPB enabled - NEEDS to be disabled"
      fix_ibpb=true
    else
      echo "IBPB disabled - CORRECT setting"
      fix_ibpb=false
    fi

    if [ `cat /sys/kernel/debug/x86/pti_enabled` = 1 ]; then
      echo "PTI enabled - CORRECT setting"
      fix_pti=false
    else
      echo "PTI disabled - NEEDS to be enabled"
      fix_pti=true
    fi

  else
    echo "/sys/kernel/debug/x86 not detected as expected."
    echo "Bailing out - $HOSTNAME should be inspected."
    exit 1
  fi
}

function fix_flags
{
  ms_changes=false

  if [ $fix_ibrs = 'true' ]; then
    echo 0 > /sys/kernel/debug/x86/ibrs_enabled
    echo "disabled IBRS"
    ms_changes=true
  fi

  if [ $fix_ibpb = 'true' ]; then
    echo 0 > /sys/kernel/debug/x86/ibpb_enabled
    echo "disabled IBPB"
    ms_changes=true
  fi

  if [ $fix_pti = 'true' ]; then
    echo 1 > /sys/kernel/debug/x86/pti_enabled
    echo "enabled PTI"
    ms_changes=true
  fi
}

# main

# Verify running as root
if [ $UID != 0 ]; then
  echo "script must be executed as root"
  exit 1
fi

orb_bundle_check
debug_mount
flag_check
fix_flags

if [ $ms_changes = "true" ]; then
  echo "Verifying changes"
  flag_check
fi