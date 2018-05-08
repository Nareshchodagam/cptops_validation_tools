#!/bin/bash
#$Id: validate_vc.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $
ps -ef |grep -q [s]vnserve
if [ $? -eq 0 ]
then
  echo "Process SVNSERVE:        [RUNNING]"
else
  echo "ERROR Process SVNSERVE:        [NOT RUNNING]"
  exit 1
fi

# get vc-master                                                                                                                                            
VCMASTER=$( getent hosts vc-commit.ops.sfdc.net | awk '{ print $2 }' )

if [[ "${HOSTNAME}" == "${VCMASTER}" ]]; then                                                                                                              
  if pidof systemd 2>&1 >/dev/null; then  
     systemctl is-active --quiet httpd
  else
     /etc/init.d/httpd status 2>&1 > /dev/null
  fi

  if [ $? -eq 0 ]
  then
    echo "Process HTTPD:        [RUNNING]"
  else
    echo "ERROR Process HTTPD:        [NOT RUNNING]"
    exit 1
  fi
fi
