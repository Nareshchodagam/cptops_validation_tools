#!/bin/bash
#
# Purpose: This script should validate that the MTA host is functioning
# after patching/reboot
#

logfile=/var/log/ecelerity/sfdclog.ec

function checkPort(){
	PORT=25
	PORTSTATUS=$(netstat -an | grep :${PORT} | grep LISTEN | wc -l)

	if [[ $PORTSTATUS -gt 0 ]]
	then
		echo "${PORTSTATUS} processes are listening on port ${PORT}"
		return 0
	else
		echo "Nothing is listening on port ${PORT}"
		return 1
	fi
}

function checkProcess(){
	PROCESS="ecelerity"
	PROCSTATUS=$(ps -ef | grep ${PROCESS} | grep -v grep | wc -l)
	if [[ $PROCSTATUS -gt 0 ]]
	then
		echo "${PROCESS} is running"
		return 0
	else
		echo "${PROCESS} is NOT running"
		return 1
	fi
}

function checkQueues(){
	ts=$(stat -c %Z /proc/)
	currenttime=$(date +"%s")
	timediff=$(( $currenttime - $ts ))

	echo "Uptime: ${timediff} seconds"

	D=0
	R=0
	T=0
	P=0
	QUEUEDIFF=0
	THRESHOLD=0.85
	LINELIMIT=1000 # Limiting the lines for performance reasons.

	while read line
	do
	        if [ $(echo ${line} | cut -d'@' -f1) -ge ${ts} ]
	        then
	                EVENTTYPE=$(echo ${line} | cut -d'@' -f 3)
	                case "$EVENTTYPE" in
	                'D')
						if [ $(echo ${line} | cut -d'@' -f13 | cut -d'.' -f1) -le ${timediff} ]
						then
	                        D=$((D+1))
	                    fi
				;;
	                'R')
	                        R=$((R+1))
	                        ;;
	                'T')
	                        T=$((T+1))
	                        ;;
	                'P')
	                        P=$((P+1))
	                        ;;
	                esac
	        fi
	done < <(tail -${LINELIMIT} ${logfile})

	if [[ $D -eq 0 || $R -eq 0 ]]
	then
		echo "Something went wrong, there is nothing in the queues"
		return 1
	else
		echo "Good. Queues are not empty."
		DIFF=$(bc <<< "scale=2; $D / $R")
		echo "Delivered - ${D} : Received - ${R} : Difference = ${DIFF}"
	fi


	# Commenting out D / R ratio check. This is not working as expected.
	# Leaving printout and removing exit on < Threshold.
	# Per Joe. Humphreys.

	#DIFF=$(bc <<< "scale=2; $D / $R")
	#echo "Delivered - ${D} : Received - ${R} : Difference = ${DIFF}"

	#if (( $(bc <<< "$DIFF <= $THRESHOLD") == 1 ))
	#then
	        #        echo "FAIL: Queue difference of ${DIFF} is below the threshold of ${THRESHOLD}"
	        #      return 1
	#else
	        #        echo "PASS: Queue difference of ${DIFF} is within the threshold of ${THRESHOLD}"
	        #       return 0
	#fi

	return 0
}

function checkMailSend(){
	address="emailreleaseverification@salesforce.com"
	scriptpath="./remote_transfer/testallbindings.sh"

	$(${scriptpath} ${address})
	if [[ $? == 0 ]]
	then

		sleep 10

		SUCCESSFULSEND=$(tail -2000 ${logfile} | grep ${address} | cut -d'@' -f3 | grep D | wc -l)
		if [[ $SUCCESSFULSEND -lt 10 ]]
		then
			echo "Only sent ${SUCCESSFULSEND} messages to ${address}"
			return 1
		fi

		echo "${SUCCESSFULSEND} messages were successfully delivered to ${address}"
		return 0

	else
		echo "Something went wrong with testallbindings.sh"
		return 1
	fi

}

function checkFailedVip(){
	LINELIMIT=500 # Limiting the lines for performance reasons.
	chkstring='@coremailprocessor@.*no MXs for this domain'

	while read line
	do
		if [[ "${line}" =~ "${chkstring}" ]]
	    then
			echo "Customer mail may be failing, please check the logs manually"
			return 1
	    fi
	done < <(tail -${LINELIMIT} ${logfile})
	return 0
}



checkPort || exit 1
checkProcess || exit 1
checkQueues || exit 1
checkMailSend || exit 1
checkFailedVip || exit 1
