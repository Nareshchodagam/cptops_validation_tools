#! /bin/bash

set -x

[ "$USER" == "logstash" ] || exit 1
cd /opt/logbus-reconciler/bin || exit 1
./consumer_launcher start || exit 1
./copykickoffrecon start || exit 1
[ -f ~/crontab.bak ] && crontab - < ~/crontab.bak || exit 1

./copykickoffrecon status | tee ~/logbus_status || exit 1
./consumer_launcher status | tee -a ~/logbus_status || exit 1

grep -i 'copykickoffrecon is running' ~/logbus_status || exit 1
grep -i 'consumer is running' ~/logbus_status || exit 1

set +x



#ssh <host>
#sudo su - logstash
#cd /opt/logbus-reconciler/bin
#./consumer_launcher start
#./copykickoffrecon start
#[ -f ~/crontab.bak ] && crontab - < ~/crontab.bak
#./copykickoffrecon status => Should be ‘copykickoffrecon is running’
#./consumer_launcher status => Should be ‘consumer is running’
