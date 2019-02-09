#! /bin/bash

# validate_polcore.sh 0.0.8
# Orlando Castro
#
# If PCE does not properly start after reboot, this script will attempt to start PCE up to 3 times.
PCE_ROOT=$( egrep install_root: /etc/illumio-pce/runtime_env.yml | awk '{print $2}' )
PCE_CTL="${PCE_ROOT}/illumio-pce-ctl"
ILOUSER='ilo-pce'
LCYAN='\033[1;36m'
LGREEN='\033[1;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color
HOSTFUNC=$( hostname | cut -f2 -d- )

check_status() {
   # After patching allow time for illumio to try and come back up on its own. Give it 3 chances...
   for i in $( seq 3 )
   do
      # If we don't see this pattern after the first pass, most likely illumio will fail to start.
      sudo -u ${ILOUSER} ${PCE_CTL} cluster-status | egrep NODES | awk -F\: '{print $3}' | egrep '[2-6] of [3-6]\)'
      case $? in
         0 )
            echo $?
            echo -e "${LGREEN}######### ${HOSTNAME} has joined the cluster #########${NC}"
            sudo -u ${ILOUSER} ${PCE_CTL} cluster-status | egrep 'status:' | egrep 'RUNNING' 2> /dev/nul
            validate_cluster;;
         * )
            echo $?
            echo -e "${YELLOW}######### ${HOSTNAME}: PCE startup FAILED! Checking again in 10 seconds. Test: $i of 3 #########${NC}"
            sleep 9;;
      esac
   done
}

start_pce() {
   # Illumio PCE failed to startup after reboot. Call kill_pce() to perform a graceful service stop.
   # If the graceful stop fails kill_pce() will apply kill -9 to all procs owned by user ilo-pce.
   kill_pce

   # With a clean slate, start the PCE:
   echo -e "${LCYAN}######### ${HOSTNAME}: PCE startup in progress.. #########${NC}"
   sudo -u ${ILOUSER} ${PCE_CTL} start
   sleep 9

   # CPT: The number of tries can be increased. It shouldn't be necessary. 
   # The cluster normally adds the host back into the fold after the first pass.
   for i in $( seq 3 )
   do
      echo "PCE start attempt: ${i} of 3"
      # We should see this pattern almost immediately after initial startup.
      # The regex is somewhat loose on purpose. The goal is to ensure successful patching.
      sudo -u ${ILOUSER} ${PCE_CTL} cluster-status | egrep NODES | awk -F\: '{print $3}' | egrep '[2-6] of [3-6]\)'
      case $? in
         0 )
            echo $?
            # Pattern match! Call validate_cluster()
            validate_cluster;;
         * )
            echo $?
            # If at first you don't succeed, try, try up to x times.
            kill_pce
            sudo -u ${ILOUSER} ${PCE_CTL} start
            sleep 18;;
      esac
   done

   # Third time wasn't a charm. Exit and show current cluster status.
   echo -e "${YELLOW}######### ${HOSTNAME} failed to join the cluster. Please contact CryptoOps #########${NC}"
   echo -e "${YELLOW}FAILURE OUTPUT:${NC}"
   sudo -u ${ILOUSER} ${PCE_CTL} cluster-status
   exit 1
}

kill_pce() {
   # Crush! Kill! Destroy!
   echo -e "${YELLOW}######### ${HOSTNAME} FAILED! Killing PCE procs and starting again... #########${NC}"
   sudo -u ${ILOUSER} ${PCE_CTL} stop
   ps auxww | egrep ilo-pc[e] && kill -9 $( ps auxww | egrep ilo-pc[e] | awk '{print $2}' )
}

validate_cluster() {
   # If we have reached this function, it should be smooth sailing from here on out...
   #
   # Set sleep time according to role
   # CPT: Adjust $sleep_duration if you need more time for startup. 54 for poldata should be good.
   # This is the only place you need to adjust the time. The other sleep durations are optimal.
   # Keep in mind sleep_duration * 9. This will also affect validate_db() 
   echo ${HOSTFUNC} | egrep 'poldata' && sleep_duration='54' || sleep_duration='27'
   echo -e "${LGREEN}######### ${HOSTNAME}: PCE startup successful. Validating cluster-status...  #########${NC}"

   # Try validating cluster up to 9 times. Typically 2 tries are enough. 
   # We can grant a little extra resilience to ensure a positive result...
   for i in $( seq 9 )
   do
      echo "Cluster validation test: ${i} of 9"
      # Looking for "Cluster status: RUNNING" That indicates a successful startup.
      sudo -u ${ILOUSER} ${PCE_CTL} cluster-status | egrep 'status:' | egrep 'RUNNING' 2> /dev/nul
      case $? in
         0 )
            echo $?
            sudo -u ${ILOUSER} ${PCE_CTL} cluster-status
            echo -e "${LGREEN}######### ${HOSTNAME}: PCE cluster status is set to RUNNING! #########${NC}"
            # If this is a poldata host, call validate_db() else exit 0
            echo ${HOSTFUNC} | egrep 'poldata' && validate_db || exit 0;;
         * )
            # Cluster status is not set to RUNNING. Sleep then test again...
            echo $?
            sleep ${sleep_duration};;
      esac
   done

   # If validate_cluster() is being called, we should never get to this point. Adding below just in case:
   echo -e "${YELLOW}######### ${HOSTNAME} had startup issues. Please contact CryptoOps #########${NC}"
   echo -e "${YELLOW}FAILURE OUTPUT:${NC}"
   sudo -u ${ILOUSER} ${PCE_CTL} cluster-status
   exit 1
}

validate_db() {
   # Verify all db related functions in the cluster are running.
   # We don't want to see any services "NOT RUNNING"
   # Should take approx 7 passes to complete.
   echo -e "${LCYAN}######### ${HOSTNAME}: DB validation in progress... #########${NC}"
   for i in $( seq 9 )
   do
      echo "DB Validation test: ${i} of 9"
      sudo -u ${ILOUSER} ${PCE_CTL} cluster-status | egrep 'NOT RUNNING' 2> /dev/nul
      case $? in
         0 )
            # String NOT RUNNING found. Sleep, then test again...
            echo $?
            sleep ${sleep_duration};;
         * )
            echo $?
            echo -e "${LGREEN}######### ${HOSTNAME}: DB validation is successful! #########${NC}"
            exit 0;;
      esac
   done

   # Any DB services in a "NOT RUNNING" state will eventually start even if this function finishes first.
   ### DB services "NOT RUNNING" will NOT break CaPTain!!! ###
   echo -e "${YELLOW}######### ${HOSTNAME}: DB validation did not complete after 9 passes. This will NOT affect CaPTain... #########${NC}"
   # Set an explicit exit 0 to ensure CaPTain does not fail.
   exit 0
}

check_status
start_pce
