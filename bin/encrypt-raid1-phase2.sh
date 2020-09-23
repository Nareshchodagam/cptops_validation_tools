#!/bin/bash

HOME=$1
HOME_TMP=${HOME}_e
LABEL=$2


MDH=$(lsblk -i -o NAME,MOUNTPOINT | grep "/$HOME$" | head -n 1 |  perl -nle 'm/(md[0-9]+)/; print $1')
MDH_TARGET_DISK=$(cat /etc/flux/.${HOME}_target_disk_plain)
NEW_MDH_STATUS=$(cat /proc/mdstat | grep $MDH_TARGET_DISK)
NEW_MDH=$(echo $NEW_MDH_STATUS | awk '{print $1}')
MDH_LUKS_UUID=$(cryptsetup luksUUID /dev/$NEW_MDH)

xfsdump -l 1 - /$HOME | xfsrestore - /$HOME_TMP

umount /$HOME_TMP

grep -w "/${HOME}/watchdog" /etc/fstab > /etc/fstab.watchdog
grep -v "/${HOME}" /etc/fstab > /etc/fstab.tmp
cat /etc/fstab.watchdog >> /etc/fstab.tmp
cp /etc/fstab.tmp /etc/fstab
echo "/dev/mapper/luks-${MDH_LUKS_UUID}        /${HOME}     xfs     defaults,noatime,_netdev,x-systemd.automount       0 0" >> /etc/fstab
