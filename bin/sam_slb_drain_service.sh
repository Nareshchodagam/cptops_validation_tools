#!/bin/bash
# Scipt to drain the BIRD service gracefully.

servicename="kubelet"
stat_check=$(systemctl status ${servicename})
if [ "$?" -ne "0" ]
then
    echo "Found ${servicename} already in stopped state"
    docker_list=$(docker ps | grep slb-iface | awk '{print $1}')
    [[ ! -z "$docker_list" ]] && echo ${docker_list} | xargs docker kill || echo "No Containers are available to kill"
    ifconfig ipvs-iface0 down
    exit 0
else
    stop_service=$(systemctl stop ${servicename})
    sleep 5
    stat_check=$(systemctl status ${servicename})
    if [ "$?" -ne "0" ]
    then
        echo "${servicename} is now stopped"
        docker_list=$(docker ps | grep slb-iface | awk '{print $1}')
        [[ ! -z "$docker_list" ]] &&  echo ${docker_list} | xargs docker kill || echo "No Containers are available to kill"
        ifconfig ipvs-iface0 down
        exit 0
    else
        exit 3
    fi
fi
