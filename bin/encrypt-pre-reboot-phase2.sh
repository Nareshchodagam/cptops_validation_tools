#!/bin/bash

  MOUNTPOINT=$1
  LABEL=$2

  MD=$(lsblk -i -o NAME,MOUNTPOINT | grep /$MOUNTPOINT$ | grep -v crypt | head -n 1 |  perl -nle 'm/(md[0-9]+)/; print $1')

  if ! [ -z "$MD" ]
  then
   echo "Can encrypt $MOUNTPOINT"
   MD_STATUS=$(cat /proc/mdstat | grep $MD)
   echo $MD_STATUS

   MD_RAID=$(echo $MD_STATUS | awk '{print $4}')
   echo $MD_RAID

   if [ $MD_RAID == "raid1" ] || [ $MD_RAID == "raid10" ]
   then
      echo "Encrypting $MD_RAID at $LABEL"
      sh remote_transfer/encrypt-${MD_RAID}-phase2.sh $MOUNTPOINT $LABEL > /tmp/encrypt-${MD_RAID}-${LABEL}-phase2.log
   fi
  fi
