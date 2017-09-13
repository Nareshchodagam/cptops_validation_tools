#!/bin/bash
#$Id: validate_syslog.sh 242300 2017-09-13 15:14:12Z rgunawan@SFDC.NET $

ROLE="syslog-ng"
SYSTEMCTL=$( command -v systemctl || echo "/bin/systemctl" )
RPM=$( command -v rpm || echo "/usr/bin/rpm" )
PGREP=$( command -v pgrep || echo "/usr/bin/pgrep" )
NETSTAT=$( command -v netstat || echo "/usr/bin/netstat" )
EXIT_CODE=0
EXIT_CODES=0

assert () {
    CMD="$@"
    ${CMD} 
    [[ $EXIT_CODE -ne 0 ]] && \
	echo '  [FAILED]'  "${CMD}" || \
	echo '  [PASSED]'  "${CMD}"
    EXIT_CODES=`expr ${EXIT_CODES} + ${EXIT_CODE}`
}

execute () {
    OUTPUT=$( eval "${@}" 2>&1 )
    EXIT_CODE=$?
}

echo -e "\n### Validation for role ${ROLE} ####\n"
# Check for systemctl status
assert execute "echo \"Check ${ROLE} is running\" && [ $( ${SYSTEMCTL} is-active ${ROLE} ) == 'active' ]" 

# Check for package version
assert execute "echo \"Check ${ROLE} package version is ${LATEST_VER}\" && [ $( ${RPM} -q ${ROLE} ) ]" 

# Check for PID process
assert execute "echo \"Check ${ROLE} PID process\" && [ $( ${PGREP} ${ROLE} ) -gt 0 ]" 

# Check if port is listening
assert execute "echo \"Check ${ROLE} port is listening\" && [ $( ${NETSTAT} -tulpn 2>&1 | grep ':514' | wc -l ) -eq 2 ]" # 514 tcp + udp 

echo -e "\nFailed Checks: ${EXIT_CODES}"
[[ ${EXIT_CODES} -eq 0 ]] && echo "Validation Result: PASSED" || echo "Validation Result: FAILED"

exit ${EXIT_CODES}
