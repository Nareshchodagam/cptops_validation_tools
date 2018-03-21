#!/bin/bash
#$Id: validate_appauth.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $
sleep 60
SITE=`hostname|cut -d"." -f1|cut -d"-" -f4`
HOSTFUNC=$(hostname | cut -f2 -d- | sed 's/[0-9]//')

REALM="ops"
APPREALM="APP.SFDC.NET"

if [ "$SITE" == "crd" ] || [ "$SITE" == "prd" ]; then REALM="eng" APPREALM="APP.ENG.SFDC.NET";fi

MASTER=`dig appkerberos.${REALM}.sfdc.net CNAME +short  | sed 's/\.$//'`


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
