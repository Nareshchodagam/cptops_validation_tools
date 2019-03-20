#!/bin/bash

# Slaves
slaves=(
"rd0-gro1-1-prd"
"rd0-gro1-2-prd"
"stmr0ops0-release1-1-prd"
"stmr0ops0-release1-2-prd"
"stmr0ops0-release1-3-prd"
"stmr0ops0-release1-4-prd"
"stmr0ops0-release1-5-prd"
"stmr0ops0-release1-6-prd"
"stmr0ops0-release2-1-prd"
"stmr0ops0-release2-2-prd"
"stmr0ops0-release2-3-prd"
"stmr0ops0-release2-4-prd"
"stmr0ops0-release2-5-prd"
)

# figure out failover host
if [ "$(hostname -a)" = "rd0-groauto1-1-prd" ]; then
	FAILOVER_HOST="rd0-groauto2-1-prd"
else
	FAILOVER_HOST="rd0-groauto1-1-prd"
fi

function stopKill {
	echo "Killing Jenkins process..."
        kill -9 $(cat jenkins.pid) > /dev/null 2>&1
        rm -rf jenkins.pid
        pgrep -f jenkins.war | xargs kill -9 > /dev/null 2>&1
}

function stopSoftly {
	echo "Stopping softly..."
	# Sent shutdown command - note: token is the git access token in //secrets/gro/githubaccount.yaml
	java -jar /usr/lib/jenkins/WEB-INF/jenkins-cli.jar -s "http://localhost:8080" -auth "gro-global:$(cat /home/build/.shutdowntoken)" safe-shutdown        

	# Stopping slaves
	for slave in "${slaves[@]}"; do
		ssh -o StrictHostKeyChecking=no -t build@${slave} "pgrep -f 'java .* remoting.jar' | xargs kill -9 > /dev/null 2>&1"
	done
}

function stopApache {
	echo "Stopping Apache..."
	sudo service httpd stop
}

function startFailover {
	while (pgrep -f jenkins.war > /dev/null); do 
		echo "Waiting for Jenkins to shutdown..."
		sleep 5
	done
	echo "Starting failover host ${FAILOVER_HOST}..."
	ssh -o StrictHostKeyChecking=no build@${FAILOVER_HOST} "/home/build/start_jenkins.sh"
}

# kill if --kill arg is found
if [[ "${@}" == *"--kill"* ]]; then
	#stopApache
	stopKill
	startFailover
fi

# do not start failover if --nostartfailover arg is found
if [[ "${@}" = *"--nostartfailover"* ]]; then
	#stopApache
	stopSoftly
else
	#stopApache
	stopSoftly
	startFailover
fi


