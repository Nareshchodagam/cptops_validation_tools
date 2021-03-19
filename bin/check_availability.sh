#/bin/bash

#Script to validate min. 50% hosts of DDI roles are healthy

IFS=':, ' read -r -a array <<< "$1"
idx=0
failedCount=0
totalHosts=0
while [ -n "${array[$idx]}" ]; do
        ping -c 1 `echo "${array[$idx]}"`
        status=$?
        if [ $status -ne 0 ]; then
                        echo "${array[$idx]} is down"
                        let failedCount=$failedCount+1
        fi

        let idx=$idx+1
        let totalHosts=$totalHosts+1
done
res=`echo "scale=2; $failedCount / $totalHosts" | bc`
res=$(echo "scale=2; $res*100" | bc)
res=${res%.*}
if [ $res -gt 50 ]; then
                echo "50% service availability criteria is not met, please check the unhealthy hosts"
                exit 1
else
                echo "50% service availability criteria is met"
fi
exit
