#!/bin/bash
#$Id: validate_vnscanam.sh 242300 2018-1-02 15:14:12Z rmurray@SFDC.NET $
if [[ -f /etc/rc.d/init.d/nessusd ]] || [[ -e /etc/systemd/system/nessusd.service ]]
then
      /bin/ps -ef | grep nessusd | grep -v grep
                if [ $? -eq 0 ]
                then
                echo "Nessus Manager :        [RUNNING]"
        else
                echo "ERROR Nessus Manager :        [NOT RUNNING]"
                exit 1
        fi
else
        echo "ERROR Nessus Manager Not Installed"
        exit 1
fi
