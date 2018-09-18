#!/bin/bash

Program_name=$0

function usage() {
    echo "usage: $Program_name <comma separated case numbers> <sso username>"
}

if [[ "$#" != "2" ]]
then
    usage
    exit 1
fi

cases=$1
cmd_user=$2

function file_exists() {
    File=$1
    if [ -f $File ]
    then
        rm $File
    fi
}

function chk_cmd() {
    local return_=1
    type  $1 >/dev/null 2>&1 &&  { local return_=0; }
    echo "$return_"
    }

function read_passwd() {
    #IFS=","
    case $1 in

        kerb)
            read -s -p "Enter krb Password: " passwd
            echo
            ;;
        gus)
            read -s -p "Enter sso password: " gus_passwd
            echo
            ;;
        "")
            read -s -p "Enter krb Password: " passwd
            read -s -p "Enter sso password: " gus_passwd
            ;;
        *)
            echo -e "Only acceptable inputs are allowed"
            ;;
    esac
    }


function screen_cmds() {
    case $1 in
        scrn)
            screen -S  $scrn_name -X screen -t $case_strip
            sleep 3
            ;;
        kz)
            cmd="katzmeow.pl --case_number  $case --username $cmd_user --impl"
            screen -S  $scrn_name -p $case_strip -X stuff "$cmd $(echo -ne '\015')"
            sleep 5
            ;;
        kerb)
            screen -S  $scrn_name -p $case_strip -X stuff  $passwd
            screen -S  $scrn_name -p $case_strip -X stuff "$(echo -ne '\015')"
            ;;
        gus)
            screen -S  $scrn_name -p $case_strip -X stuff "$(echo -ne '\015')"
            sleep 5
            screen -S  $scrn_name -p $case_strip -X stuff  $gus_passwd
            screen -S  $scrn_name -p $case_strip -X stuff "$(echo -ne '\015')"
            ;;
    esac

}

function val_uinput() {
    case $1 in
        verify_kinit)
            local return=0
            screen -S  $scrn_name -p $case_strip  -X hardcopy  /tmp/${case}.log
            if [[ `cat /tmp/${case}.log| grep  "." | tail -1` =~ "password:" ]]
            then
                    local return=1
                    echo $return
                    file_exists /tmp/${case}.log
            fi
            ;;
        verify_kerb)
            local return=0
            screen -S  $scrn_name -p $case_strip  -X hardcopy  /tmp/${case}.log
            if [[ `cat /tmp/${case}.log| grep  "." | tail -1` =~ "Kerberos" ]]
            then
                local return=1
                echo $return
                file_exists /tmp/${case}.log
            else
                local return=0
                echo $return
                file_exists /tmp/${case}.log
            fi
            ;;
        verify_uinput)
            screen -S  $scrn_name -p $case_strip  -X hardcopy  /tmp/${case}.log
            if [[ `cat /tmp/${case}.log| grep  "." | tail -1` =~ "Confirm" ]]
            then
                echo -e "`cat /tmp/${case}.log| grep  "." | tail -1`"
                file_exists /tmp/${case}.log
            fi
            ;;
        verify_gus)
            local return=0
            screen -S  $scrn_name -p $case_strip  -X hardcopy  /tmp/${case}.log
            if [[ `cat /tmp/${case}.log| grep  "." | tail -1` =~ "SSO" ]]
            then
                local return=1
                echo $return
                file_exists /tmp/${case}.log
            else
                local return=0
                echo $return
                file_exists /tmp/${case}.log
            fi
            ;;
    esac
}

function val_case() {
    uinput="y"
    screen -S  $scrn_name -p $case_strip  -X hardcopy  /tmp/${case}.log
    while [[ `cat /tmp/${case}.log| grep  "." | tail -1` =~ "[y/n]" ]]
    do

        screen -S  $scrn_name -p $case_strip -X stuff  $uinput
        screen -S  $scrn_name -p $case_strip -X stuff "$(echo -ne '\015')"
        sleep 5
        screen -S  $scrn_name -p $case_strip -X stuff "$(echo -ne '\015')"
        sleep 5
        screen -S $scrn_name -p $case_strip -X stuff "seq all"
        screen -S  $scrn_name -p $case_strip -X stuff "$(echo -ne '\015')"
        sleep 5
        screen -S $scrn_name -p $case_strip -X stuff $uinput
        sleep 5
        screen -S  $scrn_name -p $case_strip -X stuff "$(echo -ne '\015')"
        file_exists /tmp/${case}.log
        screen -S  $scrn_name -p $case_strip  -X hardcopy  /tmp/${case}.log

    done

}

function execute_screen() {
    local count=$2
    if [ "$2" -eq "0" ]
    then
        read_passwd $1
    fi
    screen_cmds $1
    sleep 5
    rtrn_code=$(val_uinput verify_$1)
    while  [ "$rtrn_code" != "0" ]
    do
        read_passwd $1
        screen_cmds $1
        sleep 5
        rtrn_code=$(val_uinput verify_$1)
    done
}

function run_cmd() {
    scrn_name=$1
    screen -S $scrn_name -A -d -m
    count=0
    IFS=","
    for case in $cases
    do
        len_cases=${#case}
        case_strip=${case:2:len_cases}
        screen_cmds scrn
        screen_cmds kz

        if [ "$count" == "0" ]
        then
            execute_screen kerb $count
            execute_screen gus $count
            val_case
            echo -e "Executing case $case in screen window $case_strip\n"

        else
            execute_screen kerb $count
            execute_screen gus $count
            val_case
            echo -e "Executing case $case in screen window $case_strip\n"
        fi
        count=`expr $count + 1`
    done
}

function chk_sessions() {
    read -r -p "Please enter a unique screen session name: " screen_name
    run_cmd $screen_name
}

# main_program
chk_sessions
