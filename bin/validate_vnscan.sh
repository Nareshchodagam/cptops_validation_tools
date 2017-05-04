#!/bin/bash
#$Id: validate_vnscan.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $
if [ -f /etc/rc.d/init.d/nexposeengine.rc ]
then
	STATUS=$(/etc/rc.d/init.d/nexposeengine.rc status)
	if [ "${STATUS}" == "NeXpose security engine is running." ]
	        then
	        echo "NeXpose security engine:        [RUNNING]"
	else
	        echo "ERROR NeXpose security engine:        [NOT RUNNING]"
	        exit 1
	fi
else 
        echo "ERROR NeXpose Not Installed"
        exit 1
fi
