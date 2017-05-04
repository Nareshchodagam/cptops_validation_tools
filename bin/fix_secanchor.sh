#!/bin/bash
# Script to validate and fix SecAnchor hosts after kernel upgrade.
# Date: 02/21/2016
# Author: Sameer Syed

#Check if the OS is detecting the Luna card
/sbin/lspci | grep -q Chrysalis
if [[ $? -ne 0 ]]
then
	echo "Luna PCI card not detected, exiting"
	exit
fi

#Check if luna driver is loaded, if check status fails, rebuild the drivers and install
/usr/safenet/lunaclient/bin/lunadiag -s=1 -c=2 | grep -q detected
if [[ $? -ne 0 ]]
then
	cd /usr/safenet/lunaclient/pcidriver
	rpmbuild --rebuild vkd-5.4.1-2.src.rpm
	rpm -e vkd
	rpm -Uvh ./x86_64/vkd-5.4.1-2.x86_64.rpm
else
	echo "Luna Driver is already loaded, proceeding to next step to check if K2K is running..."
fi

#Check and fix group on tpm0 device
grep -q tpm /etc/rc.local
if [[ $? -ne 0 ]]
then
	echo "chgrp sfdc /dev/tpm0" >> /etc/rc.local
	chgrp sfdc /dev/tpm0
fi
