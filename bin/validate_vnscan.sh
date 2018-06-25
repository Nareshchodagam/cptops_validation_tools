#!/bin/bash
#$Id: validate_vnscan.sh 242300 2018-1-02 15:14:12Z rmurray@SFDC.NET $
      /bin/ps -ef | grep nessusd | grep -v grep
                if [ $? -eq 0 ]
                then
                echo "Nessus Scanner :        [RUNNING]"
        else
                echo "ERROR Nessus Scanner :        [NOT RUNNING]"
                exit 1
        fi
