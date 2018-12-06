#!/bin/bash
#$Id: validate_auth.sh 241801 2016-11-28 16:07:57Z iviscio@SFDC.NET $

sleep 60

KRB_REALM=$(head /etc/sysconfig/krb5kdc | awk '{print $NF}')

MASTER1=$(egrep -A3 "^\s*${KRB_REALM}" /etc/krb5.conf | grep admin_server | awk '{print $NF}')
MASTER=$(dig ${MASTER1} CNAME +short | sed 's/\.$//')

[ -z "$MASTER" ] && MASTER=${MASTER1}

typeset -i RETVAL=0

if [ "${MASTER}" == `hostname` ]
then
    ps -ef | grep -q [k]admin
    RETVAL=$(( ${RETVAL} + $? ))
else
    ps -ef | grep -q [k]prop
    RETVAL=$(( ${RETVAL} + $? ))
fi

ps -ef|grep -q [k]rb5kdc
RETVAL=$(( ${RETVAL} + $? ))

if [ ${RETVAL} -eq 0 ]
then
    echo "KRB Processes:        [RUNNING]"
else
    echo "ERROR KRB Processes:        [NOT RUNNING]"
fi

if ps -ef | grep -q [r]adiusd
then
    echo "Radius Processes:        [RUNNING]"
else
    # Radius not started, check links
    [ -h /etc/raddb/sites-enabled/inner-tunnel ] && rm -f /etc/raddb/sites-enabled/inner-tunnel
    [ -h /etc/raddb/sites-enabled/control-socket ] && rm -f /etc/raddb/sites-enabled/control-socket
    # Try again
    if [ -x /usr/bin/systemctl ]
    then
        /usr/bin/systemctl start radiusd
    else
        /sbin/service radiusd start
    fi
    # And check again
    if ps -ef | grep -q [r]adiusd
    then
        echo "Radius Processes:        [RUNNING]"
    else
        echo "ERROR Radius Processes:        [NOT RUNNING]"
        RETVAL=$(( ${RETVAL} + 1 ))
    fi
fi


if ps -ef | grep -q [t]ac_plus
then
    echo "Tac_plus Processes:        [RUNNING]"
else
    echo "ERROR Tac_plus Processes:        [NOT RUNNING]"
    RETVAL=$(( ${RETVAL} + 1 ))
fi

exit ${RETVAL}
