#!/bin/bash
#$Id: validate_appauth.sh 242300 2016-12-02 15:14:12Z iviscio@SFDC.NET $
sleep 60
SITE=`hostname|cut -d"." -f1|cut -d"-" -f4`
HOSTFUNC=$(hostname | cut -f2 -d- | sed 's/[0-9]//')

REALM="ops"
APPREALM="APP.SFDC.NET"

if [ "$SITE" == "crd" ] || [ "$SITE" == "prd" ]; then REALM="eng" APPREALM="APP.ENG.SFDC.NET";fi
	
MASTER=`dig appkerberos.${REALM}.sfdc.net CNAME +short  | sed 's/\.$//'`

if [ "$MASTER" == `hostname` ];then
	CHECK_ADMIN=$(ps -ef|grep -q [k]admin); RETVAL1=$?
else	
	grep -q APP /etc/init.d/kprop
	if [ $? -eq 0 ]
	  then
	      CHECK=$(ps -ef|grep -q "[k]propd -S -r"); RETVAL1=$?
	  else
	      sed -i "s/daemon \${kpropd} -S/daemon \${kpropd} -S -r ${APPREALM}/" /etc/init.d/kprop
		  service kprop restart
		  CHECK=$(ps -ef|grep -q "[k]propd -S -r"); RETVAL1=$?
	fi
fi

CHECK_KRB=$(ps -ef|grep -q [k]rb5kdc); RETVAL2=$?
if [ ${RETVAL1} -eq 0 ] && [ ${RETVAL2} -eq 0 ]
   then
       echo "KRB Processes:        [RUNNING]"
   else
       echo "ERROR KRB Processes:        [NOT RUNNING]"
       exit 1
fi
