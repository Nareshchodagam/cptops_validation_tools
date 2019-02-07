#! /bin/bash

# validate_polcore.sh 0.0.3
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
      sudo -u ${ILOUSER} ${PCE_CTL} cluster-status | egrep NODES | awk -F\: '{print $3}' | egrep '[2-6] of [46]\)'
      case $? in
         0 )
            echo $?
            echo -e "${LGREEN}######### ${HOSTNAME} has joined the cluster #########${NC}"
            sudo -u ${ILOUSER} ${PCE_CTL} cluster-status | egrep 'status:' | egrep 'RUNNING' 2> /dev/nul
            validate;;
         * )
            echo $?
            echo -e "${YELLOW}######### ${HOSTNAME}: PCE startup FAILED! Checking again in 10 seconds. Test: $i of 3 #########${NC}"
            sleep 9;;
      esac
   done
}

start_pce() {
   # Illumio PCE failed to startup after reboot.
   # Call kill_pce() to kill all procs owned by user ilo-pce, then start service again.
   kill_pce
   echo -e "${LCYAN}######### ${HOSTNAME}: PCE startup in progress.. #########${NC}"
   sudo -u ${ILOUSER} ${PCE_CTL} start
   sleep 9
   for i in $( seq 3 )
   do
      echo "PCE start attempt: ${i} of 3"
      # We should see this pattern almost immediately after initial start:
      sudo -u ${ILOUSER} ${PCE_CTL} cluster-status | egrep NODES | awk -F\: '{print $3}' | egrep '[2-6] of [46]\)'
      case $? in
         0 )
            echo $?
            # We see the pattern! Call validate()
            validate;;
         * )
            echo $?
            # If at first you don't succeed, try, try up to 3 times.
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

validate() {
   # If we have reached this function, it should be smooth sailing from here on out...
   # Set sleep time according to role
   echo ${HOSTFUNC} | egrep 'poldata' && sleep_duration='54' || sleep_duration='27'
   echo -e "${LGREEN}######### ${HOSTNAME}: PCE startup successful. Validating cluster-status...  #########${NC}"
   # Try up to 9 times, but typically 2 tries is enough. We can grant a little extra resilience here...
   for i in $( seq 9 )
   do
      echo "Validate test ${i} of 9"
      sudo -u ${ILOUSER} ${PCE_CTL} cluster-status | egrep 'status:' | egrep 'RUNNING' 2> /dev/nul
      case $? in
         0 )
            echo $?
            sudo -u ${ILOUSER} ${PCE_CTL} cluster-status
            echo -e "${LGREEN}######### ${HOSTNAME} has successfully joined the cluster #########${NC}"
            exit 0;;
         * )
            echo $?
            # If CPT needs to add more time for Illumio startup, adjust $sleep_duration near the top of this function.
            sleep ${sleep_duration};;
      esac
   done
   # If validate() is being called, we should never get to this point. Adding below just in case...
   echo -e "${YELLOW}######### ${HOSTNAME} had startup issues. Please contact CryptoOps #########${NC}"
   echo -e "${YELLOW}FAILURE OUTPUT:${NC}"
   sudo -u ${ILOUSER} ${PCE_CTL} cluster-status
   exit 1
}

check_status
start_pce
