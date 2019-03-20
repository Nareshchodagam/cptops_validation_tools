#!/bin/bash
#export JAVA_HOME=/home/build/tools/Linux/jdk/openjdk1.8.0_181_x64
export JAVA_HOME=/home/build/tools/Linux/jdk/java-1.8.0-openjdk-1.8.0.191.b12-1.el7_6.x86_64
export PATH=$JAVA_HOME/bin:$PATH
export P4PORT=ssl:p4proxy-edg-prd.soma.salesforce.com:1999
export P4USER=gro-global

httpPort=8080
#httpListenAddress=0.0.0.0
httpListenAddress=127.0.0.1
httpsPort=8443
httpsListenAddress=127.0.0.1
#httpsListenAddress=0.0.0.0

KEYSTORE_PASSWD=$(cat /home/build/certs/secure.properties)

# figure out failover host
if [ "$(hostname -a)" = "rd0-groauto1-1-prd" ]; then
        FAILOVER_HOST="rd0-groauto2-1-prd"
else
        FAILOVER_HOST="rd0-groauto1-1-prd"
fi

function isFailoverUp {
	pid=$(ssh -o StrictHostKeyChecking=no -q -t build@${FAILOVER_HOST} "pgrep -f jenkins.war" > /dev/null; echo $?)
	if [[ "$pid" -eq "0" ]]; then
		echo "INFO: It looks like the failover host ${FAILOVER_HOST} is running so we don't need to start it here"
		exit 0
	fi
}

isFailoverUp

if [[ "${@}" == *"--nossl"* ]]; then
	httpsPort=-1
fi

if [[ "${@}" == *"--debug"* ]]; then
	java -Dfile.encoding="UTF-8" -Dcom.sun.akuma.Daemon=daemonized -Djava.awt.headless=true -Xms2048m -Xmx2048m -XX:MaxPermSize=256m -Duser.timezone=America/Los_Angeles -Dhudson.diyChunking=false -DJENKINS_HOME=/var/lib/jenkins -jar /usr/lib/jenkins/jenkins.war --logfile=/home/build/logs/jenkins/jenkins.log --webroot=/home/build/cache/jenkins/war --daemon --httpPort=${httpPort} --debug=9 --handlerCountMax=100 --handlerCountMaxIdle=20 -Dhudson.security.LDAPSecurityRealm=ALL | tail -f /home/build/logs/jenkins/jenkins.debug.log
elif [[ "${@}" == *"--service"* ]]; then
	java -Dfile.encoding="UTF-8" -Dcom.sun.akuma.Daemon=daemonized -Djava.awt.headless=true -Xms2048m -Xmx2048m -XX:MaxPermSize=256m -Duser.timezone=America/Los_Angeles -Dhudson.diyChunking=false -DJENKINS_HOME=/var/lib/jenkins -jar /usr/lib/jenkins/jenkins.war --logfile=/home/build/logs/jenkins/jenkins.log --webroot=/home/build/cache/jenkins/war --daemon --httpPort=${httpPort} --httpsPort=${httpsPort} --httpListenAddress=${httpListenAddress} --debug=0 --handlerCountMax=100 --handlerCountMaxIdle=20 -Dhudson.security.LDAPSecurityRealm=ALL > /home/build/logs/jenkins/jenkins.service.startup.log 2>&1
else
	nohup java -Dfile.encoding="UTF-8" -Dcom.sun.akuma.Daemon=daemonized -Djava.awt.headless=true -Xms2048m -Xmx2048m -XX:MaxPermSize=256m -Duser.timezone=America/Los_Angeles -Dhudson.diyChunking=false -DJENKINS_HOME=/var/lib/jenkins -jar /usr/lib/jenkins/jenkins.war --logfile=/home/build/logs/jenkins/jenkins.log --webroot=/home/build/cache/jenkins/war --daemon --httpPort=${httpPort} --httpsPort=${httpsPort} --httpListenAddress=${httpListenAddress} --debug=0 --handlerCountMax=100 --handlerCountMaxIdle=20 -Dhudson.security.LDAPSecurityRealm=ALL &> /home/build/logs/jenkins/nohup.out &
fi
