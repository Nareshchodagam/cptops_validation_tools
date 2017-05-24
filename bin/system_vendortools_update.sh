#!/bin/bash
# system update script for automation.pl, or direct invocation
# -h for options
# pass arguments via $ARGS if using automation.pl
# Git location :- https://git.soma.salesforce.com/CPT/cptops_sysfiles/bin/system_vendortools_update.sh

INSTANCE=`hostname | cut -f1 -d-`
SHORTHOST=`hostname | cut -d. -f1`
DNS_DOMAIN=`hostname | awk -F. '{print $2 "." $3 "." $4}'`
OSTYPE=
OSVERSION=
KAT_STATUS=
#Remove this when katello issues go away
KAT_BYPASS=true
SITECODE=`hostname |cut -d. -f1 | awk -F- '{print $NF}'`
if [ -r /etc/centos-release ]; then
    RH_VER=`cat /etc/centos-release |awk '{print $3}'`
    RH_VER_MAJOR=`cat /etc/centos-release |awk '{print $3}'|awk -F"." '{print $1}'`
    RH_VER_MINOR=`cat /etc/centos-release |awk '{print $3}'|awk -F"." '{print $2}'`
elif [ -r /etc/redhat-release ]; then
    RH_VER=`cat /etc/redhat-release |awk '{print $7}'`
    RH_VER_MAJOR=`cat /etc/redhat-release |awk '{print $7}'|awk -F"." '{print $1}'`
    RH_VER_MINOR=`cat /etc/redhat-release |awk '{print $7}'|awk -F"." '{print $2}'`
fi
HOSTFUNC=`hostname | cut -f2 -d- | sed 's/[0-9]$//g'`
SUDO_USERID=
status_only=0
SELF=$0
EXCLUDES=
do_reboot=0
REPO_CONF=
#Method & Force are unused for vendortools, left here for safety's sake
METHOD=full
FORCE=0

# over-ride sitecode so that we can test in piab
if [ $SITECODE == "piab" ] || [ $SITECODE == "puppetdev" ]; then
        SITECODE=sfm
        DNS_DOMAIN=ops.sfdc.net
fi

# Debug printing if KERNEL_UPDATE_DEBUG is set
# Params:
#       $1 -- message to be printed
#       $2 -- optionally, "-n" to suppress newlines
#       $3 -- optionally, ">&2" to redirect output to STDERR
function dprint {
        if [ $KERNEL_UPDATE_DEBUG ]; then
                echo $2 "[$HOSTNAME]:$1" $3
        fi
}

function do_exit {
        echo "[$HOSTNAME]:$1" >& 2
        if [ $2 == "UNSUPPORTED" ]; then
                exit 3;
        elif [ $2 == "PERMISSIONS" ]; then
                exit 4;
        elif [ $2 == "TOOLS" ]; then
                exit 5;
        elif [ $2 == "NOOP" ]; then
                exit 6
        elif [ $2 == "SUCCESS" ]; then
                exit 0;
        else
                exit 1;
        fi
}

function determine_sudo_user {
        if [ $OSTYPE != "unknown" ]; then
                # first match on userid tied to tty
                SUDO_USERID=`who -m | awk '{ print $1 }'`
                if [ ! -z $SUDO_USER ]; then
                        # the system sets SUDO_USER, so use that instead
                        SUDO_USERID=$SUDO_USER
                fi
        fi
        dprint "sudo user is [$SUDO_USERID]"
        if [ -z $SUDO_USERID ]; then
                do_exit "Unable to figure out the user id of the sudo user. Exiting." "UNSUPPORTED"
        fi
}

function fix_zshrc_prompt {
        # move out newuser script to avoid release-runner zsh issue
        ZSHVER=`rpm -qi zsh | grep Version | perl -ne 'print "$1" if /Version\s+: (\d.\d.\d{1,2}) /'`
        ZSHPATHS="/usr/share/zsh/$ZSHVER/scripts"
        ZSHPATHF="/usr/share/zsh/$ZSHVER/functions"
        if [ -f $ZSHPATHS/newuser ];then
                mv $ZSHPATHS/newuser $ZSHPATHS/_newuser
        fi
        if [ -f $ZSHPATHF/zsh-newuser-install ];then
                mv $ZSHPATHF/zsh-newuser-install $ZSHPATHF/_zsh-newuser-install
        fi
}

function determine_os_type {
		if [ -r /etc/oracle-release ]; then
				OSTYPE=OEL
                REBOOT=/usr/bin/reboot
                LOGFILE=/root/system_updated
        elif [ -r /etc/centos-release ]; then
                OSTYPE=CENTOS
                REBOOT=/usr/bin/reboot
                LOGFILE=/root/system_updated
        elif [ -r /etc/redhat-release ]; then
                OSTYPE=RHEL
                REBOOT=/usr/bin/reboot
                LOGFILE=/root/system_updated
        elif [ -r /etc/debian_version ]; then
                OSTYPE=UBUNTU
                LOGFILE=/root/system_updated
        elif [ -r /etc/release ]; then
            LOGFILE=/var/sadm/system/logs/system_updated
            if [ `uname -p` == "i386" ]; then
                OSTYPE=SOLARIS-X86
                REBOOT=/usr/sbin/reboot
            else
                OSTYPE=SOLARIS-SPARC
                REBOOT=/usr/sbin/reboot
            fi
        else
                OSTYPE=unknown
        fi
        dprint "OSTYPE=[${OSTYPE}]"
}

function determine_os_version {
		if [ $OSTYPE == "OEL" ]; then
                OSVERSION=`cat /etc/oracle-release | cut -f5 -d\ | cut -f1 -d.`
                OSPATCH=`cat /etc/oracle-release | cut -f5 -d\ | cut -f2 -d.`
                PROD_DC=`host $INSTANCE-monitor |head -1 |awk '{print $6}' |cut -d. -f1 |awk -F- '{print $NF}'`
        elif [ $OSTYPE == "CENTOS" ]; then
                OSVERSION=`cat /etc/centos-release | grep -o '[0-9]\..' | cut -c 1-1`
                OSPATCH=`cat /etc/centos-release | cut -f3 -d\ | cut -f2 -d.`
                PROD_DC=`host $INSTANCE-monitor |head -1 |awk '{print $6}' |cut -d. -f1 |awk -F- '{print $NF}'`
        elif [ $OSTYPE == "RHEL" ]; then
                OSVERSION=`cat /etc/redhat-release | grep -o '[0-9]\..' | cut -c 1-1`
                OSPATCH=`cat /etc/redhat-release | cut -f7 -d\ | cut -f2 -d.`
                PROD_DC=`host $INSTANCE-monitor |head -1 |awk '{print $6}' |cut -d. -f1 |awk -F- '{print $NF}'`
        elif [ $OSTYPE == "UBUNTU" ]; then
                OSVERSION=`lsb_release -r | cut -f2`
        elif [ $OSTYPE == "SOLARIS-X86" ] || [ $OSTYPE == "SOLARIS-SPARC" ]; then
                OSVERSION=`uname -v |cut -f2 -d_`
                OSVERSIONINT=`echo $OSVERSION |tr -d "-" |bc`
                PROD_DC=`/usr/sbin/host $INSTANCE-monitor |head -1 |awk '{print $6}' |cut -d. -f1 |awk -F- '{print $NF}'`
        else
                OSVERSION=unknown
        fi
        dprint "OSVERSION=[${OSVERSION}]"
}

function determine_puppet_host {
        if [ -f /etc/puppet/AFW_BUILD ]; then
                if [ -f /usr/bin/phaser ]; then
                        yum install -y python-sfdc-phaser -c http://ops-inst1-1-$SITECODE.$DNS_DOMAIN/media/frb/stable/$RH_VER_MAJOR/stable.repo --disablerepo=* --enablerepo=*frb_stable*
                        return 0
                else
                        return 1
                fi
        else
                return 1
        fi
}

function check_os_type_and_version {
        determine_os_type
        if [ $OSTYPE != "unknown" ]; then
                determine_os_version
        else
                do_exit "Unknown or unsupported OS" "UNSUPPORTED"
        fi

        if determine_puppet_host
        then
          echo "Host is managed by puppet"
        fi

        if [ $OSTYPE != "OEL" ] && [ $OSTYPE != "CENTOS" ] && [ $OSTYPE != "RHEL" ]; then
                do_exit "Unsupported OS [${OSTYPE}]"  "UNSUPPORTED"
        fi

        if [ $OSVERSION == "unknown" ]; then
                do_exit "Unknown version of [${OSTYPE}]" "UNSUPPORTED"
        elif [ $OSTYPE == "RHEL" ] && [ $OSVERSION -eq 4 -o $OSVERSION -eq 7 ]; then
                do_exit "[$OSTYPE][$OSVERSION] cannot be upgraded. Please reimage the machine" "UNSUPPORTED"
        fi

        dprint "[$OSTYPE][$OSVERSION] checks out. Proceeding."
}

function check_if_production {
        if [ "$PATCH_PROD" == "true" ]; then
            echo "PRODUCTION FLAG TURNED ON:  Will patch all hosts"
        else
            if [ "$PROD_DC" == "$SITECODE" ]; then
                do_exit "is in the production pod, but the -p flag to confirm production changes was not set."  "PERMISSIONS"
            fi
        fi
}

function ensure_valid_yum_config {
        repo_url=$1
        ver=$2
        yumconf=/etc/yum.conf
        yumkernelrepofile=/etc/yum.repos.d/kernel.repo
        yumrhelrepofile=/etc/yum.repos.d/rhel.repo

        if [ ! -w $yumconf ]; then
                do_exit "User [$USER] cannot write to [$yumconf]" "PERMISSIONS"
        fi

        #Disable all other repos on the host
        for enabled in `ls /etc/yum.repos.d/`; do
                sed -i 's/enabled\=1/enabled=0/' /etc/yum.repos.d/$enabled;
        done;

        #Remove ops-inst mount point if exists
        if mountpoint -q /mnt; then
          echo "Unmounting ops-inst nfs mount"
          cd /
          umount -f /mnt
        fi


#       grep 'installonlypkgs=' $yumconf
#       if [ $? -ne 0 ]; then
#               perl -pi -e 's/installonly_limit=3/installonly_limit=3\ninstallonlypkgs=kernel/g' $yumconf
#       fi

        touch $yumkernelrepofile
        if [ $? -ne 0 ]; then
                do_exit "User [$USER] cannot create file [$yumkernelrepofile]" "PERMISSIONS"
        fi

cat >$yumkernelrepofile <<EOF
[kernel]
name=Kernel update repo
baseurl=$repo_url
enabled=0
gpgcheck=0
EOF

if [ $SITECODE == "chx" ] || [ $SITECODE == "wax" ]; then
        RECOMMENDED='Recommended_x86-64'
else
        RECOMMENDED='Recommended_x86-64'
fi

        case $RH_VER_MAJOR in
           5)
if [ ! -z $ver ];then
    rhel_base="rhel$ver\_x86-64"
    updates_base="rhel$ver\_x86-64_yum"
else
    rhel_base='rhel50_Recommended_x86-64'
    updates_base="rhel50_$RECOMMENDED"
fi
cat >$yumrhelrepofile <<EOF
[rhel]
name=Red Hat Enterprise Linux
baseurl=http://ops-inst1-1-$SITECODE.ops.sfdc.net/media/$rhel_base/Server
enabled=0
gpgcheck=0


[rhel_updates]
name=Red Hat Enterprise Linux Updates
baseurl=http://ops-inst1-1-$SITECODE.ops.sfdc.net/rhel_updates/$updates_base
enabled=0
gpgcheck=0
EOF
           ;;
           6)
if [ ! -z $ver ];then
rhel_base="rhel$ver\_x86-64"
updates_base="rhel$ver\_x86-64_yum"
else
rhel_base='rhel60_Recommended_x86-64'
updates_base="rhel60_$RECOMMENDED"
fi
cat >$yumrhelrepofile <<EOF
[rhel]
name=Red Hat Enterprise Linux
baseurl=http://ops-inst1-1-$SITECODE.ops.sfdc.net/media/$rhel_base/Server
enabled=0
gpgcheck=0

[rhel_updates]
name=Red Hat Enterprise Linux Updates
baseurl=http://ops-inst1-1-$SITECODE.ops.sfdc.net/rhel_updates/$updates_base
enabled=0
gpgcheck=0
EOF
           ;;
           *)
                echo "ERROR: Unknown Major Version"
                echo "ERROR: 1"
           ;;
        esac

}

function gen_valid_repo_url {
	DEFAULT_VER="current"
	DEFAULT_REPO="$DEFAULT_VER-media,$DEFAULT_VER"

	if [ $OSTYPE == "RHEL" ]; then
		INST_SERV="http://ops-inst1-1-$SITECODE.$DNS_DOMAIN/rhel_updates/repos/RH$RH_VER_MAJOR"
	elif [ $OSTYPE == "OEL" ]; then
		DEFAULT_VER="candidate"
	 	DEFAULT_REPO="$DEFAULT_VER-media,$DEFAULT_VER"
		INST_SERV="http://ops-inst1-1-$SITECODE.$DNS_DOMAIN/rhel_updates/repos/OL$RH_VER_MAJOR"
	elif [ $OSTYPE == "CENTOS" ]; then
	 	DEFAULT_REPO="$DEFAULT_VER-media,$DEFAULT_VER"
		INST_SERV="http://ops-inst1-1-$SITECODE.$DNS_DOMAIN/rhel_updates/repos/CE$RH_VER_MAJOR"
	fi
	if [ $REPO_CANDIDATE ];then
		DEFAULT_VER="$REPO_CANDIDATE"
	 	DEFAULT_REPO="$REPO_CANDIDATE-media,$REPO_CANDIDATE"
	fi
	REPO_CONF="-c $INST_SERV/$DEFAULT_VER.repo --enablerepo=$DEFAULT_REPO"
	echo $REPO_CONF
        FRB_CONF=${REPO_CONF},*frb_stable*
}

function ensure_valid_repo_config {
        if [ $OSTYPE == "RHEL" ]; then
                repo_url="http://ops-inst1-1-$SITECODE.ops.sfdc.net/media/rhel_kernel_update/$OSVERSION"
                if [ $1 ]; then
                        repo_url=$1
                fi
                dprint "Using [$repo_url] for yum repository baseurl"
                ensure_valid_yum_config $repo_url
        else
                do_exit "Unable to configure repositories for OS [$OSTYPE]" "UNSUPPORTED"
        fi
}

function ensure_in_path {
        dprint "Checking for [$1]... " "-n"
        PROG=`which $1`
        if [ $? -ne 0 ]; then
                echo "[$1] not found in path!"
                katExit
                exit 1;
        else
                dprint "using [$PROG]"
        fi
}

function ensure_yum_has_updates_available {
        ensure_in_path yum
        yum --version > /dev/null 2>&1
        if [ $? -ne 0 ]; then
                katExit
                do_exit "YUM is malfunctioning" "TOOLS"
        fi

        $YUM --disablerepo=* $REPO_CONF check-update > /dev/null 2>&1

        result=$?

#       Non-AFW hosts are so out of date that the vendor tools names have changed.
#       As such, check-update is not useful on the first run, and not until frb repos
#       are availbe on every host as well
#
#        if [ $result -eq 0 ]; then
#                echo "System is updated to the latest rev. At [$OSTYPE][$OSVERSION]"
#                katExit
#                exit 0;
#        elif [ $result -eq 100 ]; then
#                dprint "YUM has updates available for [$OSTYPE][$OSVERSION]"
#        else
#                katExit
#                do_exit "YUM failed to run check-update" "TOOLS"
#        fi
}

function ensure_host_has_updates_available {
        if [ $OSTYPE == "RHEL" ] || [ $OSTYPE == "CENTOS" ] || [ $OSTYPE == "OEL" ]; then
                ensure_yum_has_updates_available
        else
                do_exit "Unable to check for updates for OS [$OSTYPE]" "UNSUPPORTED"
        fi
}

function check_exit {
	if [ $? -ne 0 ]; then
		echo "Failed at step $1."
                katExit
		exit 1
	fi

}

function do_actual_vendortools_update {

    # Update vendortools from FRB repo, and ONLY *stage* firmware rpms, not install
    # Setup to never fail as far as possible.
    # We're exactly midway between 8 space and 2 space alignment, let's go with 4 then

    # We only support tools on 6 and 7
    if [ $RH_VER_MAJOR -eq 5 ]
    then
        return 0
    fi

    # TODO, come up with a backup scheme for lack of dmidecode
    if [ ! -f /usr/sbin/dmidecode ]
    then
        return 0
    fi

    VENDOR=`/usr/sbin/dmidecode | grep Vendor|cut -d: -f2|awk '{print$1}'`
    if [ $VENDOR == "Dell" ]
    then
        SHORT_NAME=`/usr/sbin/dmidecode --string system-product-name | tail -n1 | cut -d' ' -f2 | tr '[:upper:]' '[:lower:]'`
    elif [ $VENDOR == "HP" ]
    then
        SHORT_NAME=`/usr/sbin/dmidecode --string bios-version | tail -n 1 | tr '[:upper:]' '[:lower:]'`
    else
        return 0
    fi

    VENDOR_LOWER=`echo $VENDOR | tr '[:upper:]' '[:lower:]'`

    if ls /etc/yum.repos.d/*frb_stable* 1> /dev/null 2>&1; then
        echo "FRB repo already exists"
    else
        FRB_INST_SRVR="http://ops-inst1-1-$SITECODE.$DNS_DOMAIN/media/frb/stable/$RH_VER_MAJOR/stable.repo"
        FRB_REPO_PATH="/etc/yum.repos.d/frb_stable.repo"
        if [ -f /usr/bin/wget ]
        then
            /usr/bin/wget -q --no-check-certificate ${FRB_INST_SRVR} -O ${FRB_REPO_PATH}
        elif [ -f /usr/bin/curl ]
        then
            /usr/bin/curl -s -k -o ${FRB_REPO_PATH} ${FRB_INST_SRVR}
        elif [ -f /usr/bin/yum-config-manager ]
        then
            yum-config-manager --add-repo=${FRB_INST_SRVR} 2>&1 > /dev/null
            mv /etc/yum.repos.d/stable.repo ${FRB_REPO_PATH}
        else
            return 0
        fi
        # This is a known issue on some systems, fix perms for use.
        chmod 644 ${FRB_REPO_PATH}
    fi

    # Install implies update
    ${YUM} -y install python-sfdc-phaser --disablerepo=* ${FRB_CONF}
    # Remove unnecessary vendor tools packages (deprecated and/or not required or in the case of dset, renamed)
    ${YUM} --disablerepo=* -y remove srvadmin-idrac-ivmcli srvadmin-oslog \
        srvadmin-libxslt delldset srvadmin-idrac7 srvadmin-racadm4 \
        srvadmin-racsvc srvadmin-rnasoap srvadmin-cm srvadmin-itunnelprovider \
        srvadmin-jre srvadmin-smweb srvadmin-standardAgent \
        srvadmin-storageservices srvadmin-tomcat srvadmin-webserver hp-ams \
        hpacucli hpssa > /dev/null 2>&1

    if [ $VENDOR == "HP" ]
    then
      ${YUM} --disablerepo=* info installed hp*.i386
      if [ $? -eq 0 ]
      then
        ${YUM} -y --disablerepo=* remove hp*.i386 > /dev/null 2>&1
      fi
      ${YUM} -y --disablerepo=* remove hponcfg.noarch > /dev/null 2>&1
    fi

    if [ $VENDOR == "Dell" ]
    then
      ${YUM} -y install compat-libstdc++-33.i686 libstdc++.i686 libxml2.i686 --disablerepo=* ${FRB_CONF}
    fi

    OLD_VERS=`repoquery -q --qf="%{name}-%{version}-%{release}-%{arch}" ${VENDOR_LOWER}-${SHORT_NAME}-tools`
    [[ -z ${OLD_VERS} ]] && OLD_VERS="None"

    # Stage firmware for any future updates that might happen on this box
    ${YUM} -y install ${VENDOR_LOWER}-${SHORT_NAME}-tools ${VENDOR_LOWER}-${SHORT_NAME}-firmware --disablerepo=* ${FRB_CONF}

    # Just in case, cleanup dupes
    if [ -f /usr/bin/package-cleanup ]
    then
        /usr/bin/package-cleanup --cleandupes -y
    fi

    if [ $VENDOR == "Dell" ]
    then
      # Dell's rpm dependencies are broken; if these packages aren't installed last, omreport won't work correctly
      ${YUM} -y reinstall srvadmin-storage-cli srvadmin-storage-snmp srvadmin-deng-snmp --disablerepo=* ${FRB_CONF}
      # Security does not like tog-pegasus
      service tog-pegasus stop
      chkconfig tog-pegasus off
      # Dell has a helpful service restart script
      dell_services=(dataeng dsm_om_shrsvc dsm_sa_ipmi instsvcdrv)
      for srv in ${dell_services[@]}
      do
        chkconfig $srv on
      done
      /opt/dell/srvadmin/sbin/srvadmin-services.sh restart
    elif [ $VENDOR == "HP" ]
    then
      # hpsmhd can cause hard lockups
      service hpsmhd stop
      chkconfig hpsmhd off

      # Used to integrate hp health agents with system snmpd
      # See https://git.soma.salesforce.com/puppet/snmpd/blob/master/templates/snmpd.erb#L45
      grep 'dlmod' /etc/snmp/snmpd.conf
      if [ $? -ne 0 ]
      then
        echo 'dlmod cmaX  /usr/lib64/libcmaX64.so' >> /etc/snmp/snmpd.conf
      fi

      hp_services=(hp-health hp-snmp-agents hp-asrd)
      for srv in ${hp_services[@]}
      do
        # TODO, handle systemctl
        chkconfig $srv on
        service $srv restart
      done
    fi

    NEW_VERS=`repoquery -q --qf="%{name}-%{version}-%{release}-%{arch}" ${VENDOR_LOWER}-${SHORT_NAME}-tools`

    return 0
}

function do_vendortools_update {
    if determine_puppet_host
    then
        # Puppet will do this for us, nothing to do here
        echo "AFW host, vendortools do not need to be updated"
        ret_code=0
    else
        if [ $TEST_MODE ]
        then
            ret_code=0
        else
            do_actual_vendortools_update
            ret_code=$?
        fi
    fi

    # Ret code is currently unused in do_host_update
    return ${ret_code}
}

function do_host_update {
        if [ $OSTYPE == "RHEL" ] || [ $OSTYPE == "CENTOS" ] || [ $OSTYPE == "OEL" ]; then
                do_vendortools_update
                if [ $do_reboot == "1" ]; then
                  reboot_host
                fi
        else
                do_exit "Unable to update and reboot OS [$OSTYPE]" "UNSUPPORTED"
        fi
}

function reboot_host {
        if [ $OSTYPE == "RHEL" ] || [ $OSTYPE == "OEL" ] || [ $OSTYPE == "CENTOS"] ; then
                if [ $warn_and_wait -gt 0 ]; then
                        if [ $TEST_MODE ]; then
                          echo "Test Mode: shutdown -r +$warn_and_wait \"The vendor rpms were updated and node $HOSTNAME needs to be (optionally) rebooted\""
                        else
                          /sbin/shutdown -r +$warn_and_wait "The vendor rpms were updated and node $HOSTNAME needs to be (optionally) rebooted"
                        fi
                else
                        if [ $TEST_MODE ]; then
                                echo "Test Mode: echo \"[`date`] [$SUDO_USERID] [$HOSTNAME] [vendor tools updated from {$OLD_VERS} to {$NEW_VERS}]\" >> $LOGFILE"
                                echo "Test Mode: /usr/bin/reboot"
                        else
                                echo "[`date`] [$SUDO_USERID] [$HOSTNAME] [vendor tools updated from {$OLD_VERS} to {$NEW_VERS}]" >> $LOGFILE
                                $REBOOT
                        fi
                fi
        else
                echo "Don't know how to reboot the host"
                exit 1
        fi
}

# Katello functions
function katStatus() {
    KAT_STATUS=`subscription-manager status | grep "Overall Status" | awk {' print $3'}`
    if [ "$KAT_STATUS" == "Current" ] || [ "$KAT_STATUS" == "Invalid" ] || [ "$KAT_STATUS" == "Insufficient" ]; then
        KAT_STATUS="true"
    else
        KAT_STATUS="false"
    fi
    echo $KAT_STATUS
}

function katRepos {
    if [ -n  $REPO_CANDIDATE ] ;then
        KAT_BUNDLE=`echo $REPO_CANDIDATE | tr "." "_"`
    fi
    if [ $OSTYPE == "RHEL" ]; then
        REPO_CONF="--enablerepo=prodinfra_rhel${RH_VER_MAJOR}_$KAT_BUNDLE*"
    elif [ $OSTYPE == "CENTOS" ]; then
        REPO_CONF=" --enablerepo=prodinfra_centos${RH_VER_MAJOR}_$KAT_BUNDLE*"
    fi

    if [ $SITECODE == "chx" ] || [ $SITECODE == "wax" ]; then
        if [ $OSTYPE == "RHEL" ]; then
            REPO_CONF="--enablerepo=rhel-6-*,prodinfra_*"
        elif [ $OSTYPE == "CENTOS" ]; then
             REPO_CONF=" --enablerepo=prodinfra_Centos*"
        fi
    fi
    # Enabling Katello repos and fetching latest config
    subscription-manager config --rhsm.manage_repos=1
    subscription-manager repos
}

function katExit {
    if [ "$KAT_STATUS" == "true" ]; then
       echo "Disabling Katello repositories"
       subscription-manager config --rhsm.manage_repos=0
    fi
}

function chk_quiet_mode {
    if [ "$QUIET" == "true" ]; then
        YUM="yum -q"
    else
        YUM="yum"
    fi
    }


function usage {
        echo "Usage: $0 [options], where options are:"
        echo "  -b              bypass katello (default)"
        echo "  -d              run with debug output"
        echo "  -h              print help and exit"
        echo "  -a              candidate repo to use"
        echo "  -r <repo_url>   use separate <repo_url> as the location of the kernel package repository"
        echo "  -s              only configure the repository and check if there are pending updates, but do not apply them or reboot the machine"
        echo "  -t              run in test mode, where changes are echoed but not executed"
        echo "  -w <min>        reboot the machine, and warn all users on the machine that it will be rebooted in <min> minutes"
        echo "  -e              reboot the machine"
        echo "  -q              run in quiet mode"
        echo "  -n              diable katello bypass"
}

function main {
        warn_and_wait=0
        while getopts "dfcbqhpra:stw:e" OPTION; do
                case $OPTION in
                        b)
                                KAT_BYPASS=true
                                ;;
                        d)
                                export KERNEL_UPDATE_DEBUG=1
                                ;;
                        h)
                                usage
                                exit 0
                                ;;
                        p)
                                PATCH_PROD=true
                                ;;
                        r)
                                REPO_OVERRIDE=$OPTARG
                                ;;
                        a)
                                REPO_CANDIDATE=$OPTARG
                                ;;
                        s)
                                status_only=1
                                ;;
                        t)
                                export TEST_MODE=1
                                ;;
                        w)
                                warn_and_wait=$OPTARG
                                if [ $warn_and_wait -lt 0 ]; then
                                        echo "When using -w, time to wait cannot be less than 0 minutes"
                                        exit 1
                                fi
                                do_reboot=1
                                ;;
                        e)
                                if [ $warn_and_wait -gt 0 ]; then
                                        echo "Cannot specify -e and -w together"
                                        exit 1
                                fi
                                do_reboot=1
                                ;;
                        q)
                                QUIET=true
                                ;;
                        n)
                                unset KAT_BYPASS
                                ;;
                        *)
                                usage
                                exit 1
                                ;;
                esac
        done
        chk_quiet_mode
        check_os_type_and_version
        if [ "$PATCH_PROD" == "true" ]; then
            check_if_production
        fi

        if [ $OSTYPE == "RHEL" ] || [ $OSTYPE == "CENTOS" ]; then
            if [ "$KAT_BYPASS" != "true" ]; then
                if [ $SITECODE != "sfm" ]  && [ $SITECODE != "crz" ] && [ $SITECODE != "sfz" ]; then
                    katStatus
                    if [ $KAT_STATUS == "true" ]; then
                        echo "Fetching latest repos from Katello"
                        katRepos
                    else
                        gen_valid_repo_url
                    fi
                else
                    gen_valid_repo_url
                fi
            else
                echo "Skipping katello"
                gen_valid_repo_url
            fi
        elif [ $OSTYPE == "OEL" ]; then
            gen_valid_repo_url
        fi

        if [ $OSTYPE == "RHEL" ] || [ $OSTYPE == "CENTOS" ] || [ $OSTYPE == "OEL" ]; then
            ensure_host_has_updates_available
        fi

        determine_sudo_user
        if [ $status_only -eq 1 ]; then
                katExit
                do_exit "$SELF -s exited successfully" "SUCCESS"
        else
                do_host_update
                katExit
                do_exit "$SELF exited successfully" "SUCCESS"
        fi
}

# Verify running as root
if [ $UID != 0 ]; then
  echo "$SELF must be executed as root"
  usage
  exit 1
fi

# ARGS is passed by automation.pl, else use $@
if [ -z "$METHOD" ]; then
  METHOD="unstated"
fi

if [ -z "$ARGS" ] ; then
  main $@
else
  main $ARGS
fi
