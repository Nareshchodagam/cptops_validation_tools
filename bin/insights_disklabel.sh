#!/bin/bash

ROOTP=`lsblk -o NAME,MOUNTPOINT,LABEL -nrsdt | grep '/ ' | awk '{print $1}'`
BOOTP=`lsblk -o NAME,MOUNTPOINT,LABEL -nrsdt | grep '/boot' | awk '{print $1}'`
if [ ! ${ROOTP} ] || [ ! ${BOOTP} ]; then
    exit 1
else
    tune2fs -L root /dev/$ROOTP
    tune2fs -L boot /dev/$BOOTP
fi
