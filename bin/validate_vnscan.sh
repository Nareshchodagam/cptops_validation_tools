#!/bin/bash
#$Id: validate_vnscan.sh 242300 2018-1-02 15:14:12Z rmurray@SFDC.NET $
if [ -f /etc/rc.d/init.d/nessusd ]
then
      /bin/ps -ef | grep nessusd | grep -v grep
                if [ $? -eq 0 ]
                then
                echo "Nessus Scanner :        [RUNNING]"
        else
                echo "ERROR Nessus Scanner :        [NOT RUNNING]"
                exit 1
        fi
else
        echo "ERROR Nessus Scanner Not Installed"
        exit 1
fi
