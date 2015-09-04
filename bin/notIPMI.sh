#!/bin/bash

# notIPMI.sh - a script to replace IPMItool functionality for Dell and HP hosts
# Created by PJ Perger in October 2014
# This script's main purpose is to assist in the execution of Gigantor workflows.
# But, it can surely be used for other purposes.

# Changelog
# 11/21/2014: Added commands to return iDRAC/iLO firmware version, BIOS version, service tag.
# 11/25/2014: Added command to return power status.
# 02/05/2015: Increased expect timeout to 30 seconds. (W-2491398)

# To do:    - Consider using getopts to make arguement parsing more pleasant

# Notes:    - UEFI and Legacy BIOS will have different numerical addressing for boot devices on HP hosts.
#               - To be considered when new HP SKU arrives.

readonly PROGNAME=$(basename $0)
readonly PROGDIR=$(readlink -m $(dirname $0))
readonly ARGS="$@"

# keep track of whether individual functions for a given command succeed or fail.
# vendor-specific function results (0 or 1) are appended to vendor-specific array.
# these are global because it was too cumbersome, at the time, to do otherwise.
dell_exit_codes=()
hp_exit_codes=()

# notIPMI.sh exit codes
#
# [DELL|HP] all commands succeed                        exit 0
# [ANY]     all commans for one vendor succeed          exit 0
# [DELL|HP] one or more commands fail                   exit 99
# [ANY]     one or more commands for either vendor fail exit 98
# invalid parameters                                    exit 3

usage() {
    echo ""
    echo "$PROGNAME - a script to set the boot device and/or reboot a Dell or HP server"
    echo ""
    echo "          note: if vendor is not specified, ANY is chosen."
    echo "          note: <host> is likely in the ib.sfdc.net domain!"
    echo ""
    echo "          $PROGNAME reboot <host> <user> [DELL|HP|ANY]"
    echo "          - simply reboot a host"
    echo ""
    echo "          $PROGNAME setboot <host> <user> HDD|PXE [DELL|HP|ANY]"
    echo "          - set the boot device for a host"
    echo ""
    echo "          $PROGNAME onetime <host> <user> HDD|PXE [DELL|HP|ANY]"
    echo "          - perform a one-time reboot to the specified device"
    echo ""
    echo "          $PROGNAME firmware <host> <user> [DELL|HP|ANY]"
    echo "          - return the iDRAC or iLO firmware version"
    echo ""
    echo "          $PROGNAME bios <host> <user> [DELL|HP|ANY]"
    echo "          - return the BIOS version"
    echo ""
    echo "          $PROGNAME tag <host> <user> [DELL|HP|ANY]"
    echo "          - return the service tag"
    echo ""
    echo "          $PROGNAME power_status <host> <user> [DELL|HP|ANY]"
    echo "          - return the server's power status"
    echo ""
}

# for a given array of error codes:
# return 0 if all error codes are 0
# return 1 if one or more error codes are not 0
#
# vendor argument is use to specify array.
check_exit_codes() {
    local vendor=$1

    # is there a better way to do this?

    if [ $vendor = 'DELL' ]; then
        for value in ${dell_exit_codes[@]}; do
            if [ $value -ne 0 ]; then
                echo 1
                return
            fi
        done
        echo 0
    fi

    if [ $vendor = 'HP' ]; then
        for value in ${hp_exit_codes[@]}; do
            if [ $value -ne 0 ]; then
                echo 1
                return
            fi
        done
        echo 0
    fi
}

# ensure host and user are not blank
validate_host_and_user() {
    local host=$1
    local user=$2

    if [ -z $host ] || [ -z $user ]; then
        echo 'host or user cannot be blank!'
        usage
        exit 3
    fi
}

# ensure device is not blank
# ensure device is HDD or PXE
validate_device() {
    local device=$1

    if [ -z $device ]; then
        echo 'device cannot be blank!'
        usage
        exit 3
    fi

    if [ $device != 'HDD' ] && [ $device != 'PXE' ]; then
        echo "Invalid parameter in $FUNCNAME!"
        usage
        exit 3
    fi
}

# ensure vendor is not blank
# ensure vendor is DELL or HP
# note: this function is not currently used
validate_vendor() {
    local vendor=$1

    if [ -z $vendor ]; then
        echo 'vendor cannot be blank!'
        usage
        exit 3
    fi

    if [ $vendor != 'DELL' ] && [ $vendor != 'HP' ] && [ $vendor != 'ANY' ]; then
        echo "Invalid parameter in $FUNCNAME!"
        usage
        exit 3
    fi
}



# get password via terminal
# would be nice to embed a newline in the 'read' command, but anything echoed is absorbed by the variable calling this function
get_password() {
    v_DATACENTER=$(hostname | awk -F- '{print substr($NF,1,3)}')
    local user=$1
    local password=$(svn cat svn://vc-$v_DATACENTER/subversion/jumpstart/kickstart/sysfiles/S95drac | grep cipher_privs | awk '{print $5}')
    #read -s -r -p "Enter Password for $user: " password
    echo $password
}

### for the following vendor-specific functions, each appends its exit code to its vendor-specific array
### if more than one command exists in a function, all must succeed in order to return 0

# [DELL] enable persistent boot
dell_disable_boot_once() {
    local host=$(echo $1 | tr "," "\n")
    local user=$2
    local password=$3
    local result=''
    for hosts in $host
    do
    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user ${hosts}.ib.sfdc.net -oStrictHostKeyChecking=no -oCheckHostIP=no "racadm config -g cfgServerInfo -o cfgServerBootOnce 0"
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied"              {puts "Invalid password for $host!"; exit 4}
        timeout                              {puts "Failed to set Dell boot once to 0! for server $hosts"; exit 4}
        eof                                  {puts "Failed to set Dell boot once to 0! for server $hosts"; exit 4}
        "Object value modified successfully" {puts "Successfully set Dell boot once to 0 for server $hosts."; exit 0}
    }
EOD

    result=$?
    dell_exit_codes+=($result)
    echo "Result of dell_disable_boot_once: $result"
    done
}

# [DELL] boot to the current first boot device just once
# (disable persistent boot for one reboot)
dell_set_boot_once() {
    local host=$1
    local user=$2
    local password=$3
    local result=''

    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user $host -oStrictHostKeyChecking=no -oCheckHostIP=no "racadm config -g cfgServerInfo -o cfgServerBootOnce 1"
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied"              {puts "Invalid password for $host!"; exit 4}
        timeout                              {puts "Failed to set Dell boot once to 1! for server $hosts"; exit 4}
        eof                                  {puts "Failed to set Dell boot once to 1! for server $hosts"; exit 4}
        "Object value modified successfully" {puts "Successfully set Dell boot once to 1."; exit 0}
    }
EOD

    result=$?
    dell_exit_codes+=($result)
    echo "Result of dell_set_boot_once: $result"
}

# [DELL] set boot device
dell_set_boot_device() {
    local host=$(echo $1 | tr "," "\n")
    local user=$2
    local device=$3
    local password=$4
    local result=''
    for hosts in $host
    do
    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user ${hosts}.ib.sfdc.net -oStrictHostKeyChecking=no -oCheckHostIP=no "racadm config -g cfgServerInfo -o cfgServerFirstBootDevice $device"
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied"              {puts "Invalid password for $host!"; exit 4}
        timeout                              {puts "Failed to set Dell boot device to $device! for server $hosts"; exit 4}
        eof                                  {puts "Failed to set Dell boot device to $device! for server $hosts"; exit 4}
        "Object value modified successfully" {puts "Successfully set Dell boot device to $device for server $hosts."; exit 0}
    }
EOD

    result=$?
    dell_exit_codes+=($result)
    echo "Result of dell_set_boot_device: $result"
    done
}

# [DELL] reboot host
dell_reboot() {
    local host=$1
    local user=$2
    local password=$3
    local result=''

    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user $host -oStrictHostKeyChecking=no -oCheckHostIP=no "racadm serveraction hardreset"
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied"             {puts "Invalid password for $host!"; exit 4}
        timeout                             {puts "Failed to Dell reboot $host!"; exit 4}
        eof                                 {puts "Failed to Dell reboot $host!"; exit 4}
        "Server power operation successful" {puts "Successful Dell reboot of $host."; exit 0}
    }
EOD

    result=$?
    dell_exit_codes+=($result)
    echo "Result of dell_reboot: $result"
}

# [DELL] return iDRAC firmware version
dell_firmware() {
    local host=$1
    local user=$2
    local password=$3
    local version=''
    local result=''

    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user $host -oStrictHostKeyChecking=no -oCheckHostIP=no "racadm getversion"
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied"              {puts "Invalid password for $host!"; exit 4}
        timeout                              {puts "Failed to get Dell iDRAC firmware version for $host!"; exit 4}
        eof                                  {puts "Failed to get Dell iDRAC firmware version for $host!"; exit 4}
        -re "iDRAC Version\\\s+=\\\s(\\\S+)" {puts "Successfully got Dell iDRAC firmware version for $host."; puts "iDRAC firmware version: \$expect_out(1,string)"; exit 0}
    }
EOD

    result=$?
    dell_exit_codes+=($result)
    echo "Result of dell_firmware: $result"
}

# [DELL] return BIOS version
dell_bios() {
    local host=$1
    local user=$2
    local password=$3
    local version=''
    local result=''

    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user $host -oStrictHostKeyChecking=no -oCheckHostIP=no "racadm getversion"
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied"             {puts "Invalid password for $host!"; exit 4}
        timeout                             {puts "Failed to get Dell BIOS version for $host!"; exit 4}
        eof                                 {puts "Failed to get Dell BIOS version for $host!"; exit 4}
        -re "Bios Version\\\s+=\\\s(\\\S+)" {puts "Successfully got Dell BIOS version for $host."; puts "BIOS version: \$expect_out(1,string)"; exit 0}
    }
EOD

    result=$?
    dell_exit_codes+=($result)
    echo "Result of dell_bios: $result"
}

# [DELL] return service tag
dell_tag() {
    local host=$1
    local user=$2
    local password=$3
    local version=''
    local result=''

    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user $host -oStrictHostKeyChecking=no -oCheckHostIP=no "racadm getsysinfo"
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied"            {puts "Invalid password for $host!"; exit 4}
        timeout                            {puts "Failed to get Dell service tag for $host!"; exit 4}
        eof                                {puts "Failed to get Dell service tag for $host!"; exit 4}
        -re "Service Tag\\\s+=\\\s(\\\S+)" {puts "Successfully got Dell service tag for $host."; puts "Service tag: \$expect_out(1,string)"; exit 0}
    }
EOD

    result=$?
    dell_exit_codes+=($result)
    echo "Result of dell_tag: $result"
}

# [DELL] return server's power status
dell_power_status() {
    local host=$1
    local user=$2
    local password=$3
    local version=''
    local result=''

    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user $host -oStrictHostKeyChecking=no -oCheckHostIP=no "racadm getsysinfo"
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied"            {puts "Invalid password for $host!"; exit 4}
        timeout                            {puts "Failed to get Dell power status for $host!"; exit 4}
        eof                                {puts "Failed to get Dell power status for $host!"; exit 4}
        -re "Power Status\\\s+=\\\s(\\\S+)" {puts "Successfully got Dell power status for $host."; puts "Power status: \$expect_out(1,string)"; exit 0}
    }
EOD

    result=$?
    dell_exit_codes+=($result)
    echo "Result of dell_power_status: $result"
}

# [HP] boot to the current first boot device just once
# (currently not supported for HP hosts)
hp_set_boot_once() {

    local host=$1
    local user=$2
    local password=$3
    local result=''

    echo 'Sorry, HP does not support boot once!'

    result=4
    hp_exit_codes+=($result)
    echo "Result of hp_set_boot_once: $result"
}

# [HP] set boot device
# we actually set second boot device and first boot device
hp_set_boot_device() {
    local host=$(echo $1 | tr "," "\n")
    local user=$2
    local device=$3
    local password=$4
    local result=''
    local temp_result=''
    local temp_exit_codes=()
    local pri=''
    local sec=''
    local secondary=''

    if [ $device = 'HDD' ]; then
        pri='bootsource3'
        sec='bootsource5'
        secondary='PXE'
    fi

    if [ $device = 'PXE' ]; then
        pri='bootsource5'
        sec='bootsource3'
        secondary='HDD'
    fi
    for hosts in $host
    do
    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user ${hosts}.ib.sfdc.net -oStrictHostKeyChecking=no -oCheckHostIP=no "set /system1/bootconfig1/$sec bootorder=2"
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied" {puts "Invalid password for $host!"; exit 4}
        timeout                 {puts "Failed to set HP second boot device to $secondary on host $hosts"; exit 4}
        eof                     {puts "Failed to set HP second boot device to $secondary on host $hosts"; exit 4}
        "status=0"              {puts "Successfully set HP second boot device to $secondary on $hosts."; exit 0}
    }
EOD

    temp_result=$?
    temp_exit_codes+=($temp_result)

    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user ${hosts}.ib.sfdc.net -oStrictHostKeyChecking=no -oCheckHostIP=no "set /system1/bootconfig1/$pri bootorder=1"
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied" {puts "Invalid password for $host!"; exit 4}
        timeout                 {puts "Failed to set HP boot device to $device on host $hosts"; exit 4}
        eof                     {puts "Failed to set HP boot device to $device on host $hosts"; exit 4}
        "status=0"              {puts "Successfuly set HP boot device to $device on host $hosts."; exit 0}
    }
EOD

    temp_result=$?
    temp_exit_codes+=($temp_result)

    # return 0 only if both commands succeed
    if [[ ${temp_exit_codes[*]} =~ 4 ]]; then
        result=1
    else
        result=0
    fi

    hp_exit_codes+=($result)
    echo "Result of hp_set_boot_device: $result"
    done
}

# [HP] reboot host
hp_reboot() {
    local host=$1
    local user=$2
    local password=$3
    local result=''

    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user $host -oStrictHostKeyChecking=no -oCheckHostIP=no "reset /system1"
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied" {puts "Invalid password for $host!"; exit 4}
        timeout                 {puts "Failed to HP reboot $host!"; exit 4}
        eof                     {puts "Failed to HP reboot $host!"; exit 4}
        "Resetting server"      {puts "Successful HP reboot of $host."; exit 0}
    }
EOD

    result=$?
    hp_exit_codes+=($result)
    echo "Result of hp_reboot: $result"
}

# [HP] return iLO firmware version
hp_firmware() {
    local host=$1
    local user=$2
    local password=$3
    local version=''
    local result=''

    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user $host -oStrictHostKeyChecking=no -oCheckHostIP=no "show /map1/firmware1 version"
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied" {puts "Invalid password for $host!"; exit 4}
        timeout                 {puts "Failed to get HP iLO firmware version for $host!"; exit 4}
        eof                     {puts "Failed to get HP iLO firmware version for $host!"; exit 4}
        -re "version=(\\\S+)"   {puts "Successfully got HP iLO firmware version for $host."; puts "iLO firmware version: \$expect_out(1,string)"; exit 0}
    }
EOD

    result=$?
    hp_exit_codes+=($result)
    echo "Result of hp_firmware: $result"
}

# [HP] return BIOS version
hp_bios() {
    local host=$1
    local user=$2
    local password=$3
    local version=''
    local result=''

    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user $host -oStrictHostKeyChecking=no -oCheckHostIP=no "show /system1/firmware1 version"
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied" {puts "Invalid password for $host!"; exit 4}
        timeout                 {puts "Failed to get HP BIOS version for $host!"; exit 4}
        eof                     {puts "Failed to get HP BIOS version for $host!"; exit 4}
        -re "version=(\\\S+)"   {puts "Successfully got HP BIOS version for $host."; puts "BIOS version: \$expect_out(1,string)"; exit 0}
    }
EOD

    result=$?
    hp_exit_codes+=($result)
    echo "Result of hp_bios: $result"
}

# [HP] return service tag
hp_tag() {
    local host=$1
    local user=$2
    local password=$3
    local version=''
    local result=''

    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user $host -oStrictHostKeyChecking=no -oCheckHostIP=no "show /system1 number"
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied" {puts "Invalid password for $host!"; exit 4}
        timeout                 {puts "Failed to get HP service tag for $host!"; exit 4}
        eof                     {puts "Failed to get HP service tag for $host!"; exit 4}
        -re "number=(\\\S+)"    {puts "Successfully got HP service tag for $host."; puts "Service tag: \$expect_out(1,string)"; exit 0}
    }
EOD

    result=$?
    hp_exit_codes+=($result)
    echo "Result of hp_tag: $result"
}

# [HP] return server's power status
hp_power_status() {
    local host=$1
    local user=$2
    local password=$3
    local version=''
    local result=''

    /usr/bin/expect <<EOD
    log_user 0
    set timeout 30
    spawn ssh -l $user $host -oStrictHostKeyChecking=no -oCheckHostIP=no
    expect -re {.+password.+$}
    send "$password\r"
    expect {
        -re "Permission denied"        {puts "Invalid password for $host!"; exit 4}
        timeout                        {puts "Failed to get HP power status for $host!"; exit 4}
        eof                            {puts "Failed to get HP power status for $host!"; exit 4}
        -re "Server Power:\\\s(\\\S+)" {puts "Successfully got HP power status for $host."; puts "Power status: [string toupper \$expect_out(1,string)]"; exit 0}
    }
EOD

    result=$?
    hp_exit_codes+=($result)
    echo "Result of hp_power_status: $result"
}

main() {
    local password=''

    # identify script command and shift arguments
    local command=${1:-''}
    shift

    #  ensure command is not blank
    if [ -z $command ]; then
        echo 'Command required!'
        usage
        exit 3
    fi

     # for each command, do the following:
     # if vendor is specified, fail if any single function fails
     # if vendor is specified, succeed if all functions succeed
     # if vendor is not specified, fail if any single function for either vendor fails
     # if vendor is not specified, succeed if all functions for either vendor succeed

    case "$command" in

    reboot)
        local host=${1:-''}
        local user=${2:-''}
        local vendor=${3:-'ANY'}

        validate_host_and_user $host $user
        password=$(get_password $user)

        if [ $vendor = 'DELL' ] || [ $vendor = 'ANY' ]; then
            dell_reboot $host $user $password
            [ $vendor = 'DELL' ] && [ "$(check_exit_codes DELL)" -eq 1 ] && exit 99
            [ "$(check_exit_codes DELL)" -eq 0 ] && exit 0
        fi

        if [ $vendor = 'HP' ] || [ $vendor = 'ANY' ]; then
            hp_reboot $host $user $password
            [ $vendor = 'HP' ] && [ "$(check_exit_codes HP)" -eq 1 ] && exit 99
            [ "$(check_exit_codes HP)" -eq 0 ] && exit 0
        fi
        ;;
    setboot|onetime)
        local host=${1:-''}
        local user=${2:-''}
        local device=${3:-''}
        local vendor=${4:-'ANY'}

        validate_host_and_user $host $user
        validate_device $device
        password=$(get_password $user)

        if [ $vendor = 'DELL' ] || [ $vendor = 'ANY' ]; then

            if [ $command = 'setboot' ]; then
                dell_disable_boot_once $host $user $password
                [ $vendor = 'DELL' ] && [ "$(check_exit_codes DELL)" -eq 1 ] && exit 99
                dell_set_boot_device $host $user $device $password
                [ $vendor = 'DELL' ] && [ "$(check_exit_codes DELL)" -eq 1 ] && exit 99
                [ "$(check_exit_codes DELL)" -eq 0 ] && exit 0
            fi

            if [ $command = 'onetime' ]; then
                dell_set_boot_once $host $user $password
                [ $vendor = 'DELL' ] && [ "$(check_exit_codes DELL)" -eq 1 ] && exit 99
                dell_set_boot_device $host $user $device $password
                [ $vendor = 'DELL' ] && [ "$(check_exit_codes DELL)" -eq 1 ] && exit 99
                dell_reboot $host $user $password
                [ $vendor = 'DELL' ] && [ "$(check_exit_codes DELL)" -eq 1 ] && exit 99
                [ "$(check_exit_codes DELL)" -eq 0 ] && exit 0
            fi

        fi

        if [ $vendor = 'HP' ] || [ $vendor = 'ANY' ]; then

            if [ $command = 'setboot' ]; then
                hp_set_boot_device $host $user $device $password
                [ $vendor = 'HP' ] && [ "$(check_exit_codes HP)" -eq 1 ] && exit 99
                [ "$(check_exit_codes HP)" -eq 0 ] && exit 0
            fi

            if [ $command = 'onetime' ]; then
                hp_set_boot_once $host $user $password
                [ $vendor = 'HP' ] && [ "$(check_exit_codes HP)" -eq 1 ] && exit 99
                [ "$(check_exit_codes HP)" -eq 0 ] && exit 0
            fi

        fi
        ;;
    firmware)
        local host=${1:-''}
        local user=${2:-''}
        local vendor=${3:-'ANY'}

        validate_host_and_user $host $user
        password=$(get_password $user)

        if [ $vendor = 'DELL' ] || [ $vendor = 'ANY' ]; then
            dell_firmware $host $user $password
            [ $vendor = 'DELL' ] && [ "$(check_exit_codes DELL)" -eq 1 ] && exit 99
            [ "$(check_exit_codes DELL)" -eq 0 ] && exit 0
        fi

        if [ $vendor = 'HP' ] || [ $vendor = 'ANY' ]; then
            hp_firmware $host $user $password
            [ $vendor = 'HP' ] && [ "$(check_exit_codes HP)" -eq 1 ] && exit 99
            [ "$(check_exit_codes HP)" -eq 0 ] && exit 0
        fi
        ;;
    bios)
        local host=${1:-''}
        local user=${2:-''}
        local vendor=${3:-'ANY'}

        validate_host_and_user $host $user
        password=$(get_password $user)

        if [ $vendor = 'DELL' ] || [ $vendor = 'ANY' ]; then
            dell_bios $host $user $password
            [ $vendor = 'DELL' ] && [ "$(check_exit_codes DELL)" -eq 1 ] && exit 99
            [ "$(check_exit_codes DELL)" -eq 0 ] && exit 0
        fi

        if [ $vendor = 'HP' ] || [ $vendor = 'ANY' ]; then
            hp_bios $host $user $password
            [ $vendor = 'HP' ] && [ "$(check_exit_codes HP)" -eq 1 ] && exit 99
            [ "$(check_exit_codes HP)" -eq 0 ] && exit 0
        fi
        ;;
    tag)
        local host=${1:-''}
        local user=${2:-''}
        local vendor=${3:-'ANY'}

        validate_host_and_user $host $user
        password=$(get_password $user)

        if [ $vendor = 'DELL' ] || [ $vendor = 'ANY' ]; then
            dell_tag $host $user $password
            [ $vendor = 'DELL' ] && [ "$(check_exit_codes DELL)" -eq 1 ] && exit 99
            [ "$(check_exit_codes DELL)" -eq 0 ] && exit 0
        fi

        if [ $vendor = 'HP' ] || [ $vendor = 'ANY' ]; then
            hp_tag $host $user $password
            [ $vendor = 'HP' ] && [ "$(check_exit_codes HP)" -eq 1 ] && exit 99
            [ "$(check_exit_codes HP)" -eq 0 ] && exit 0
        fi
        ;;
    power_status)
        local host=${1:-''}
        local user=${2:-''}
        local vendor=${3:-'ANY'}

        validate_host_and_user $host $user
        password=$(get_password $user)

        if [ $vendor = 'DELL' ] || [ $vendor = 'ANY' ]; then
            dell_power_status $host $user $password
            [ $vendor = 'DELL' ] && [ "$(check_exit_codes DELL)" -eq 1 ] && exit 99
            [ "$(check_exit_codes DELL)" -eq 0 ] && exit 0
        fi

        if [ $vendor = 'HP' ] || [ $vendor = 'ANY' ]; then
            hp_power_status $host $user $password
            [ $vendor = 'HP' ] && [ "$(check_exit_codes HP)" -eq 1 ] && exit 99
            [ "$(check_exit_codes HP)" -eq 0 ] && exit 0
        fi
        ;;
    *)
        echo 'Invalid command!'
        usage
        exit 3
        ;;
    esac

    # at this point, if we haven't exited 0 then we've failed
    echo "No task completed 100% successfully!"
    exit 98
}

main "$@"
