#! /bin/bash

set -x

[ "$USER" == "logstash" ] || exit 1

cd /opt/logbus-reconciler/bin || exit 1
./consumer_launcher stop || exit 1
./copykickoffrecon stop || exit 1
crontab -l > ~/crontab.bak || exit 1
crontab -r || exit 1

TESTSTOP=$(ps -ef | egrep "(consumer)|(kickoff)|(housekeeper)" | grep -v grep | wc -l) || exit 1 
 
[ $TESTSTOP -eq 0 ] || exit 1

set +x


#ssh <hostsh <host>
#sudo su - logstash
#cd /opt/logbus-reconciler/bin
#./consumer_launcher stop
#./copykickoffrecon stop  => This can take several minutes
#crontab -l > ~/crontab.bak
#crontab -r
#ps -ef | egrep "(consumer)|(kickoff)|(housekeeper)" | grep -v grep | wc -l  => Should be ‘0’.
