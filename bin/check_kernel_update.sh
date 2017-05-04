#!/bin/bash
# $Id: check_kernel_update.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $

grep -q "exclude=kernel*" /etc/yum.conf
if [ $? -eq 0 ]
then
  echo "Kernel EXCLUDED, you can progress with patching"
else
  echo "ERROR: Kernel patch is NOT excluded! Kernel patch will break the app. Please add <exclude=kernel*> to  /etc/yum.conf on `hostname` "
  exit 1
fi
