#!/bin/bash

###############################
# CIS Benchmark CentOS 7 v2.1.1
###############################
CIS_LEVEL=1
INCLUDE_UNSCORED=0
WIDTH=79
if [ $CIS_LEVEL -gt 1 ];then
  RESULT_FIELD=10
else
  RESULT_FIELD=6
fi
MSG_FIELD=$(($WIDTH - $RESULT_FIELD))
RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
YELLOW=$(tput setaf 3)
NC=$(tput sgr0)
PASSED_CHECKS=0
FAILED_CHECKS=0

function header() {
    local HEADING=$1
    local TEXT=$((${#HEADING}+2))
    local LBAR=5
    local RBAR=$(($WIDTH - $TEXT - $LBAR))
    echo ""
    for (( x=0; x < $LBAR; x++));do
        printf %s '#'
    done
    echo -n " $HEADING "
    for (( x=0; x < $RBAR; x++));do
        printf %s '#'
    done
    echo ""
}

function msg() {
  printf "%-${MSG_FIELD}s" " - ${1}"
}

function success_result() {
    PASSED_CHECKS=$((PASSED_CHECKS+1))
    local RESULT="$GREEN${1:-PASSED}$NC"
    printf "%-${RESULT_FIELD}s\n" $RESULT
}

function failed_result() {
    FAILED_CHECKS=$((FAILED_CHECKS+1))
    local RESULT="$RED${1:-FAILED}$NC"
    printf "%-${RESULT_FIELD}s\n" $RESULT
}

function warning_result() {
    local RESULT="$YELLOW${1:-NOT CHECKED}$NC"
    printf "%-${RESULT_FIELD}s\n" $RESULT
}

function check_retval_eq_0() {
  RETVAL=$1
  if [ $RETVAL -eq 0 ]; then
    success_result
  else
    failed_result
  fi
}

function check_retval_ne_0() {
  RETVAL=$1
  if [ $RETVAL -ne 0 ]; then
    success_result
  else
    failed_result
  fi
}
##################################
    # 1.1.22 auditd Enabled
    ##################################
    header "1.1.22 Ensure auditd is enabled"
    msg " systemctl is-enabled auditd  "
    if ! [[ $(systemctl is-enabled auditd 2>&1) =~ ^enabled$ ]];then
        failed_result
    else
        success_result
    fi


###############################################
      # 1.6.1.2 Ensure the SELinux state is enforcing
      ###############################################

          header "1.6.1.2 Ensure the SELinux state is enforcing"
          msg ' grep SELINUX=enforcing /etc/selinux/config'
          grep SELINUX=enforcing /etc/selinux/config 2>&1 > /dev/null
          check_retval_eq_0 $?


#####################################
    # 5.2.15 Ensure SSH access is limited
    #####################################
    header "5.2.15 Ensure SSH access is limited"
    msg 'grep "^AllowUsers" /etc/ssh/sshd_config'
    grep "^AllowUsers" /etc/ssh/sshd_config 2>&1 > /dev/null
    check_retval_eq_0 $?

    msg 'grep "^AllowGroups" /etc/ssh/sshd_config'
    grep "^AllowGroups" /etc/ssh/sshd_config 2>&1 > /dev/null
    check_retval_eq_0 $?

    msg 'grep "^DenyUsers" /etc/ssh/sshd_config'
    grep "^DenyUsers" /etc/ssh/sshd_config 2>&1 > /dev/null
    check_retval_eq_0 $?

    msg 'grep "^DenyGroups" /etc/ssh/sshd_config'
    grep "^DenyGroups" /etc/ssh/sshd_config 2>&1 > /dev/null
    check_retval_eq_0 $?


#############################################
    # 6.1.10 Ensure no world writable files exist
    #############################################
    header "  Ensure no world writable files exist  "
    msg "df --local -P ... "
    if [[ $(df --local -P | awk '{if (NR!=1) print $6}' | xargs -I '{}' find '{}' -xdev -type f -perm -0002) =~ ^$ ]];then
        success_result
    else
        failed_result
    fi

##################################
    # 1.5.4 Ensure telnet client is not installed
    ##################################
    header "1.5.4 Ensure telnet client is not installed"
    msg 'rpm -q telnet'
    if [[ "$(rpm -q telnet)" == "package telnet is not installed" ]];then
        success_result
    else
        failed_result
    fi

##############
# FINAL REPORT
##############
for (( x=0; x < $(($WIDTH+1)); x++));do
    printf %s '='
done
printf "\n"
printf "%$(($WIDTH - 4))s" "TOTAL CHECKS: "
printf "%4s\n" "$(($PASSED_CHECKS + $FAILED_CHECKS))"
printf "%$(($WIDTH - 4))s" "FAILED CHECKS: "
printf "%4s\n" "$FAILED_CHECKS"
printf "%$(($WIDTH - 4))s" "PASSED CHECKS: "
printf "%4s\n" "$PASSED_CHECKS"
