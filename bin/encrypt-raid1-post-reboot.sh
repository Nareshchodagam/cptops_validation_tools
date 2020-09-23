#!/bin/bash

HOME=$1
LABEL=$2

MDH_SRC_DISK=$(cat /etc/flux/.${HOME}_src_disk_plain)
OLD_MDH=$(lsblk -i -o NAME,MOUNTPOINT | grep $MDH_SRC_DISK -A 1 | tail -n 1 | perl -nle 'm/(md[0-9]+)/; print $1')
MDH=$(lsblk -i -o NAME,MOUNTPOINT | grep "$HOME$" -B 1 | head -n 1 | perl -nle 'm/(md[0-9]+)/; print $1')
grep -w "/${HOME}/watchdog" /etc/fstab > /etc/fstab.watchdog
grep -v "/${HOME}" /etc/fstab > /etc/fstab.tmp
cat /etc/fstab.watchdog >> /etc/fstab.tmp
cp /etc/fstab.tmp /etc/fstab
echo "LABEL=${LABEL}        /${HOME}     xfs     defaults,noatime,_netdev,x-systemd.automount       0 0" >> /etc/fstab

mdadm --stop /dev/$OLD_MDH
mdadm --remove /dev/$OLD_MDH
mdadm --add /dev/$MDH /dev/$MDH_SRC_DISK
