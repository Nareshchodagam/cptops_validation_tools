#! /bin/bash
# Naresh Chodagam
LGREEN='\033[1;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

check_status() {
      cd /opt/raphty/bin/
      sudo raphtyctl status
  if [ $? == 0 ]
then
  echo -e "${LGREEN}######### ${HOSTNAME}: Raphty validation has been completed succesfully! #########${NC}"
    exit 0
else
 echo  echo -e "${YELLOW}######### ${HOSTNAME} cluster status failed. Please contact Raphty team #########${NC}"
exit 1
fi
}
check_status
