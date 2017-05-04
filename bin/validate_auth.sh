#!/bin/bash
#$Id: validate_auth.sh 241801 2016-11-28 16:07:57Z iviscio@SFDC.NET $

sleep 60
SITE=`hostname|cut -d"." -f1|cut -d"-" -f4`

if [ "$SITE" == "crd" ]; then REALM='eng'; else REALM='ops';fi
MASTER=`dig kerberos.${REALM}.sfdc.net CNAME +short  | sed 's/\.$//'`

if [ "$MASTER" == `hostname` ];then
	CHECK_ADMIN=$(ps -ef|grep -q [k]admin); RETVAL1=$?
else
	CHECK_ADMIN=$(ps -ef|grep -q [k]prop); RETVAL1=$?
fi
CHECK_KRB=$(ps -ef|grep -q [k]rb5kdc); RETVAL2=$?
if [ ${RETVAL1} -eq 0 ] && [ ${RETVAL2} -eq 0 ]
        then
        echo "KRB Processes:        [RUNNING]"
else
        echo "ERROR KRB Processes:        [NOT RUNNING]"
        exit 1
fi
