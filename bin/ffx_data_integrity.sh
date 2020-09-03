#!/bin/bash

#The followng script is used for data integrity validation for FFX Centos6 to Centos7 migration
#It checks disk utilization,checksum pre and post migration.
#This script needs to be executed as root , as it requires write permissions to /ffx/
#PIE team owns this script and will be handed over to CPT team for execution
#email: PIE <pie@salesforce.com>
#Author: vegallapati@salesforce.com


FFX_PATH="/ffx/temp"
DISK_UTIL="_disk_util"
CHKSUM="_chksum"

data_integrity_validation()
{
  if [ -d $FFX_PATH ]; then
    du -h $FFX_PATH | tail -1 > /ffx/$FLAG$DISK_UTIL
    if [ $? -eq 0 ]; then
      echo "Disk utilization captured $FLAG migration"
    else
      echo "Couldn't capture disk utilization, $FLAG migration.Check if the User has write permissions to /ffx/"
      exit 1
    fi
    cksum $FFX_PATH/ffxcheck.txt > /ffx/$FLAG$CHKSUM
    if [ $? -eq 0 ]; then
      echo "Checksum captured $FLAG migration"
    else
      echo "Couldn't capture checksum , $FLAG mgiration.Check if the User has write permissions to /ffx/"
      exit 1
    fi
    if [ $FLAG = "post" ]; then
      if [[ -f /ffx/$FLAG$DISK_UTIL && -f /ffx/$FLAG$CHKSUM ]]; then
        echo "Post data integration checks....Successful"
        echo
        echo "Validating the diff between Pre and Post Migration"
      fi
      diff /ffx/pre_disk_util /ffx/post_disk_util && diff /ffx/pre_chksum /ffx/post_chksum
      if [ $? -eq 0 ]; then
        echo "Data Integrity Check Pre and Post Migration....PASSED"
      else
        echo "Data Integrity Check Pre and Post Migration....FAILED"
        exit 1
      fi
    fi
  fi
}

main()
{
  # Pre-requisites required.
  # 1. This Script must run as root user , as it should have write permissions to /ffx/
  if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root.Please execute as root"
    exit 1
  fi
  # 2. The host on which this script is being executed should have /ffx/temp and /ffx/temp/ffxcheck.txt
  if [[ ! -d $FFX_PATH && ! -f $FFX_PATH/ffxcheck.txt ]]; then
    echo "Please check if this host contains /ffx/temp and /ffx/temp/ffxcheck.txt"
    exit 1
  fi
  FLAG=pre
  if [[ ! -f /ffx/$FLAG$DISK_UTIL &&  ! -f /ffx/$FLAG$CHKSUM ]]; then
    data_integrity_validation $FLAG
    if [[ -s /ffx/$FLAG$DISK_UTIL && -s /ffx/$FLAG$CHKSUM  ]]; then
      echo
      echo "Pre data integration checks....Successful"
      echo "cat /ffx/$FLAG$CHKSUM"
      cat /ffx/$FLAG$CHKSUM
    else
      echo "Pre data integration checks....Failed"
      echo "cat /ffx/$FLAG$CHKSUM"
      cat /ffx/$FLAG$CHKSUM
      exit 1
    fi
  else
    FLAG=post
    data_integrity_validation $FLAG
  fi
}
#Calling the main function
main
