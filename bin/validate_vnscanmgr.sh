#!/bin/bash
#$Id: validate_vnscanmgr.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $

chkconfig nexposeconsole.rc --list |grep -q "3:on"
if [ $? -eq 0 ]
then
    STATUS=$(/etc/init.d/nexposeconsole.rc status)
    if [ "${STATUS}" == "NeXpose security console is running." ]
            then
            echo "NeXpose security console:        [RUNNING]"
    else
            echo "ERROR NeXpose security console:        [NOT RUNNING]"
            exit 1
    fi
else 
        echo "NeXpose Not configured to start on boot"
fi
