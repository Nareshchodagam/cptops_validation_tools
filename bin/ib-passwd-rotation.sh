#!/bin/bash

# This script changes password for the admin account on the inband interface.
#
# Error Codes:
# 2 - DELL OM packages not installed
# 3 - Admin user not present
# 4 - IPMItool not found
#

# Variables for automation.pl
SITE=`hostname |cut -d'.' -f1  | cut -d'-' -f4`
INST="ops-inst1-1-$SITE"

# When changing the password, comment out the existing one rather than replacing it.

# Previous passwords
#ADMIN_PW='sun.sun'

# New password to be used (make sure to update password and increment version by one)
ADMIN_PW=''
VERSION=0001

OS=`uname -s`
echo "OS=$OS"
SHORTHOST=`hostname | awk -F\. '{print $1}'`
if [ "$OS" == "Linux" ]; then
        if [ `/usr/sbin/dmidecode -t 1 | grep -wc Dell` -ge 1 ]; then
                MAKE="Dell"
		OS_VER="RHEL`awk '{print $(NF-1)}' /etc/redhat-release`"
        fi
        if [ `/usr/sbin/dmidecode -t 1 | grep -wc HP` -ge 1 ]; then
                MAKE="HP"
		OS_VER="RHEL`awk '{print $(NF-1)}' /etc/redhat-release`"
        fi
        if [ `/usr/sbin/dmidecode -t 1 | grep -wc VMware` -ge 1 ]; then
                MAKE="VMware"
        fi
        if [ `/usr/sbin/dmidecode -t 1 | grep -wc SUN` -ge 1 ]; then
                MAKE="Sun"
		OS_VER="OracleLinux`awk '{print $NF}' /etc/oracle-release`"
        fi
elif [ "$OS" == "SunOS" ]; then
        MAKE="Sun"
        OS_VER=`uname -sr | sed 's/\ //g'`
else
        MAKE="Unkown"
fi
echo "OS_VER=$OS_VER"
echo -e "MAKE=$MAKE\n"

function set_admin_passwd_dell {
	if [ -x /usr/sbin/racadm ]; then
		RACADM=/usr/sbin/racadm
    elif [ -x /opt/dell/srvadmin/sbin/racadm ]; then
        RACADM=/opt/dell/srvadmin/sbin/racadm
	else
		echo "$SHORTHOST - Can't find /usr/sbin/racadm... Dell OM packages not installed."
		exit 2
	fi
	ADMIN=`$RACADM getconfig -g cfgUserAdmin -i 2 | grep cfgUserAdminUserName | awk -F= '{print $2}'`
	if [ "$ADMIN" != "admin" ]; then
		echo "$SHORTHOST - DRAC 'admin' user not present...  Please check DRAC setup..."
		exit 3
	fi
	$RACADM config -g cfgUserAdmin -o cfgUserAdminPassword -i 2 $ADMIN_PW 2>&1
	echo "$SHORTHOST - DRAC 'admin' user password changed"
	echo "dell_drac_admin_pw" `date +%m\/%d\/%Y' '%H:%M:%S` $VERSION >> /var/log/ib-cred-history
	echo "$VERSION" >> /var/log/ib-cred-version
}

function try_hponcfg {
    # Thanks mbaehr for creating this function!
    #
    # hponcfg "intermittenly" (frequently) fails to communicate with the iLO
    # We want to back off and retry if this occurs.
    # A declining rather than increasing backoff seems to be the key here.
    #
    # More specific errors mean that it actually communicated successfully
    # and just couldn't make the desired change - we consider those a success.

    HPONCFG='/sbin/hponcfg'
    if [ ! -x $HPONCFG ]; then
                echo -e "\t--- $HPONCFG NOT existed."
                FAILED_COUNT=$[$(echo $FAILED_COUNT) + 1]
        break;  
        fi
    TRIES=0
    for backoff in 5 5 5 5 5 5 5 5 5 5 DONE; do
        ((++TRIES))
        if ! ERROR=$($HPONCFG $@ 2>&1 1>/tmp/$SHORTHOST.hponcfg.out.$$.xml); then
            case $ERROR in
                *"Unable to communicate"*|*"Error processing the XML"*|*"A general system error"*)
                    if ! [ $backoff == "DONE" ]; then
                        echo "- [$TRIES/10] Generic failure: \"$ERROR\"; sleeping $backoff seconds"
                        sleep $backoff;
                        continue;
                    else
                        echo "- [$TRIES/10] Generic failure: \"$ERROR\"; returning"
                        break
                    fi  
                ;;  
                *)
                    echo "- [$TRIES/10] Specific failure: \"$ERROR\"; returning"
                    break;
                ;;  
            esac
        else
            echo "- [$TRIES/10] Success; returning"
            break;
        fi
    done
}

function set_admin_passwd_hp {
    # some hosts may not have the admin account in iLO, so to make sure, I'll first delete the account then add it back.
    cat <<EOF > /tmp/del_ilo_account.xml
<!-- Delete iLO User Accounts -->
<!-- Requires input of %LOGINNAME% -->
<RIBCL version="2.2">
  <LOGIN USER_LOGIN="x" PASSWORD="y">
     <USER_INFO MODE="write">
        <DELETE_USER USER_LOGIN="%LOGINNAME%"/>
     </USER_INFO>
  </LOGIN>
</RIBCL>
EOF
    try_hponcfg -f /tmp/del_ilo_account.xml -s USERNAME=admin,LOGINNAME=admin
    rm -f /tmp/del_ilo_account.xml

    # now add admin account with new password
	cat <<EOF > /tmp/cfg_ilo_admin_account.xml
<!-- Configure iLO New User Accounts Settings -->
<!-- Requires input of %USERNAME%, %LOGINNAME%, and %PASSWORD% -->
<RIBCL version="2.2">
  <LOGIN USER_LOGIN="x" PASSWORD="y">

    <RIB_INFO mode="write">
      <MOD_GLOBAL_SETTINGS>
        <MIN_PASSWORD VALUE="7"/>
      </MOD_GLOBAL_SETTINGS>
    </RIB_INFO>

    <USER_INFO MODE="write">
        <ADD_USER USER_NAME="%USERNAME%" USER_LOGIN="%LOGINNAME%" PASSWORD="%PASSWORD%">
          <RESET_SERVER_PRIV value="Y" />
          <ADMIN_PRIV value="Y" />
          <REMOTE_CONS_PRIV value="Y" />
          <RESET_SERVER_PRIV value="Y" />
          <VIRTUAL_MEDIA_PRIV value="Y" />
          <CONFIG_ILO_PRIV value="Y" />
        </ADD_USER>
    </USER_INFO>
  </LOGIN>
</RIBCL>
EOF

	try_hponcfg -f /tmp/cfg_ilo_admin_account.xml -s USERNAME=admin,LOGINNAME=admin,PASSWORD=$ADMIN_PW
	rm -f /tmp/cfg_ilo_admin_account.xml
	echo "$SHORTHOST - iLO 'admin' user password changed"
	echo "hp_ilo_admin_pw" `date +%m\/%d\/%Y' '%H:%M:%S` $VERSION >> /var/log/ib-cred-history
echo "$VERSION" >> /var/log/ib-cred-version
}

function set_admin_passwd_sun {
	if [ -x /usr/bin/ipmitool ]; then
		echo "/usr/bin/ipmitool sunoem cli 'set /SP/users/admin password=$ADMIN_PW' $ADMIN_PW" >> /tmp/ib-passwd-change.$$
	elif [ -x /usr/sbin/ipmitool ]; then
		echo "/usr/sbin/ipmitool sunoem cli 'set /SP/users/admin password=$ADMIN_PW' $ADMIN_PW" >> /tmp/ib-passwd-change.$$
	else
		echo "$SHORTHOST - ERROR:  No ipmitool found"
		exit 4
	fi

	/bin/bash /tmp/ib-passwd-change.$$
	rm -f /tmp/ib-passwd-change.$$
	echo "$SHORTHOST - ILOM 'admin' user password changed"
	echo "sun_ilom_admin_pw" `date +%m\/%d\/%Y' '%H:%M:%S` $VERSION >> /var/log/ib-cred-version
}

case $MAKE in
    Dell)
        set_admin_passwd_dell
        ;;
	HP)
		set_admin_passwd_hp
		;;
	Sun)
		set_admin_passwd_sun
		;;
	*)
		echo "No match hardware for IB..."
		;;
	esac

