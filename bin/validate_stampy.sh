#! /bin/bash
# Naresh Chodagam
LGREEN='\033[1;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

check_status() {
      sudo cd /opt/stampy/bin/
      sudo stampyctl cluster 
  if [ $? == 0 ]
then
   validate_stampy
else
 echo  echo -e "${YELLOW}######### ${HOSTNAME} cluster status failed. Please contact stampy team #########${NC}"  
exit 1
fi  
}

validate_stampy() {
         
   touch /tmp/simple.txt
   sudo stampyctl sign files --format=cms /tmp/simple.txt
   if [ $? == 0 ]
 then
    echo -e "${LGREEN}######### ${HOSTNAME}: stampy validation has been completed succesfully! #########${NC}" 
    exit 0

 esle 
   
   echo -e "${YELLOW}######### ${HOSTNAME} Stampy validation failed. Please contact stampy team #########${NC}"
   exit 1
 fi 

}

check_status
