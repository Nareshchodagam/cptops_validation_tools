#!/bin/bash
# A Lynagh 2/Aug/2018 - W-5275272

if [[ `systemctl is-enabled bro` == enabled ]]
then
  ps -ef |grep -q [b]ro
  if [ $? -eq 0 ]
  then
    echo "Process BRO:        [RUNNING]"
  else
    echo "ERROR Process BRO:        [NOT RUNNING]"
    exit 1
  fi
elif [[ `systemctl is-enabled suricata` == enabled ]]
then
  ps -ef |grep -q suricata
  if [ $? -eq 0 ]
  then
    echo "Process SURICATA:        [RUNNING]"
  else
    echo "ERROR Process SURICATA:        [NOT RUNNING]"
    exit 2
  fi
fi
