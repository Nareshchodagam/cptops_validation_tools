#!/bin/bash
# system update script for automation.pl, or direct invocation
# -h for options
# pass arguments via $ARGS if using automation.pl
# $Id: system_update.sh 204007 2016-03-31 06:59:04Z sbhathej@SFDC.NET $
# Git location :- https://git.soma.salesforce.com/CPT/cptops_sysfiles/bin/system_update.sh

INSTANCE=`hostname | cut -f1 -d-`
SHORTHOST=`hostname | cut -d. -f1`
DNS_DOMAIN=`hostname | awk -F. '{print $2 "." $3 "." $4}'`
OSTYPE=
OSVERSION=
KAT_STATUS=
SITECODE=`hostname |cut -d. -f1 | awk -F- '{print $NF}'`
if [ -r /etc/centos-release ]; then
    RH_VER=`cat /etc/centos-release |awk '{print $3}'`
    RH_VER_MAJOR=`cat /etc/centos-release |awk '{print $3}'|awk -F"." '{print $1}'`
    RH_VER_MINOR=`cat /etc/centos-release |awk '{print $3}'|awk -F"." '{print $2}'`
    if [ $RH_VER_MAJOR != "6" ]; then
       RH_VER=`cat /etc/centos-release |awk '{print $4}'`
       RH_VER_MAJOR=`cat /etc/centos-release |awk '{print $4}'|awk -F"." '{print $1}'`
       RH_VER_MINOR=`cat /etc/centos-release |awk '{print $4}'|awk -F"." '{print $2}'`
    fi
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
METHOD=full
FORCE=0
REPO_CONF=
if [ -f /etc/grub.conf ]
then
  GRUB_CONF="/etc/grub.conf"
elif [ -f /boot/grub/grub.conf ]
then
  GRUB_CONF="/boot/grub/grub.conf"
elif [ -f "/etc/grub2.cfg" ]
then
  GRUB_CONF="/etc/grub2.cfg"
fi

# over-ride sitecode so that we can test in piab
if [ $SITECODE == "piab" ] || [ $SITECODE == "puppetdev" ]; then
        SITECODE=sfm
        DNS_DOMAIN=ops.sfdc.net
fi

# Remove old kernels so there is free space in /boot
function cleanup_stale_initramfs
{
     if  [ -f  /boot/initramfs-.img ] ;then
	rm -f /boot/initramfs-.img
         echo  "Stale initramfs removed"
     else
         echo "No Stale file found skipping.."
    fi
}

function do_kernel_cleanup
{
	rpm -q yum-utils > /dev/null 2>&1
        if [ $? -ne 0 ];then
                $YUM -y --disablerepo=* $REPO_CONF install yum-utils
        fi
        package-cleanup --disablerepo=* -y --oldkernels --count=1
}

function do_fix_ramfs
{
		if [ "$RH_VER_MAJOR" != "7" ]; then
        	KERNVER=`uname -r`
        	VER=`grep kernel ${GRUB_CONF} | grep -v "${KERNVER}" | grep -v '#' | sed -e 's/^.*kernel //g' | cut -d' ' -f1 | sed -e 's/.*vmlinuz-//g'`
        	if [ -z $VER ] ; then
            	echo "Only one kernel found, so skipping the initramfs generation..."
			else
             	/sbin/depmod -a $VER
             	/sbin/dracut -f /root/initramfs-${VER}.img ${VER}
             	mv /root/initramfs-${VER}.img /boot/
			fi
		fi
}

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

function do_rc_sysinit_fix {
        # kernel upgrade moves the rc.sysinit to rc.sysinit.rpmsave
        if [ -f /etc/rc.d/rc.sysinit.rpmsave ];then
                echo "Putting old rc.sysinit back"
                mv /etc/rc.d/rc.sysinit /etc/rc.d/rc.sysinit.`date +"%Y%m%d%H%M"`
                mv /etc/rc.d/rc.sysinit.rpmsave /etc/rc.d/rc.sysinit
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
                return 0
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

        if [ $OSTYPE != "OEL" ] && [ $OSTYPE != "CENTOS" ] && [ $OSTYPE != "RHEL" ] && [ $OSTYPE != "SOLARIS-X86" ] && [ $OSTYPE != "SOLARIS-SPARC" ]; then
                do_exit "Unsupported OS [${OSTYPE}]"  "UNSUPPORTED"
        fi

# if host is > 5 years old, it may require multiple reboots on patchset
        if [ $OSTYPE == "SOLARIS-X86" ] && [ $OSVERSIONINT -lt 11885536 ]; then
          do_exit "Host's kernel level to old to allow one pass update.  Reimage host" "UNSUPPORTED"
        fi

        if [ $OSTYPE == "SOLARIS-SPARC" ] && [ $OSVERSIONINT -lt 11883336 ]; then
          do_exit "Host's kernel level to old to allow one pass update.  Reimage host" "UNSUPPORTED"
        fi

        if [ $OSTYPE == "SOLARIS-SPARC" ] && [ `uname -m` == "sun4v" ]; then
          check_sparc_firmware
# sun4v must have firmware newer than 6.4.6 or will panic with 147440-02+
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
    DEFAULT_SERV="ops-inst1-1-$SITECODE.$DNS_DOMAIN"

    if [ $(curl -o /dev/null -s -w '%{http_code}' http://$DEFAULT_SERV/media/current-base-c7/RPM-GPG-KEY-CentOS-7) != "200" ]; then
        DEFAULT_SERV="ops-inst2-1-$SITECODE.$DNS_DOMAIN"
        if [ $(curl -o /dev/null -s -w '%{http_code}' http://$DEFAULT_SERV/media/current-base-c7/RPM-GPG-KEY-CentOS-7) != "200" ]; then
            echo "ERROR: inst servers not available"
            exit 1;
        fi
    fi

	if [ $OSTYPE == "RHEL" ]; then
		INST_SERV="http://$DEFAULT_SERV/rhel_updates/repos/RH$RH_VER_MAJOR"
	elif [ $OSTYPE == "OEL" ]; then
		DEFAULT_VER="candidate"
	 	DEFAULT_REPO="$DEFAULT_VER-media,$DEFAULT_VER"
		INST_SERV="http://$DEFAULT_SERV/rhel_updates/repos/OL$RH_VER_MAJOR"
	elif [ $OSTYPE == "CENTOS" ]; then
	 	DEFAULT_REPO="$DEFAULT_VER-media,$DEFAULT_VER"
		INST_SERV="http://$DEFAULT_SERV/rhel_updates/repos/CE$RH_VER_MAJOR"
	fi
	if [ $REPO_CANDIDATE ];then
		DEFAULT_VER="$REPO_CANDIDATE"
	 	DEFAULT_REPO="$REPO_CANDIDATE-media,$REPO_CANDIDATE"
	fi
	REPO_CONF="-c $INST_SERV/$DEFAULT_VER.repo --enablerepo=$DEFAULT_REPO"
	echo $REPO_CONF
}

function add_ffx_snmp {
	if [ $OSTYPE == "RHEL" ] || [ $OSTYPE == "CENTOS" ]; then
		grep -q realStorageUnits /etc/snmp/snmpd.conf
		if [ $? -eq 1 ]; then
			echo "Added realStorageUnits clause to snmpd.conf on $HOSTNAME"
			echo "realStorageUnits 0" >> /etc/snmp/snmpd.conf
		fi
	fi
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

        $YUM --disablerepo=* $REPO_CONF clean all > /dev/null 2>&1
        $YUM --disablerepo=* $REPO_CONF check-update > /dev/null 2>&1

        result=$?
        if [ $result -eq 0 ]; then
                echo "System is updated to the latest rev. At [$OSTYPE][$OSVERSION]"
                katExit
                exit 0;
        elif [ $result -eq 100 ]; then
                dprint "YUM has updates available for [$OSTYPE][$OSVERSION]"
        else
                katExit
                do_exit "YUM failed to run check-update" "TOOLS"
        fi
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

function do_rhel_update {
        if [ $TEST_MODE ]; then
                echo "Test Mode: Will run yum --disablerepo=* -y $REPO_CONF --exclude kudzu\* upgrade"
        else
        		#if [ $SITECODE == "chx" ] || [ $SITECODE == "wax" ]; then
                    #yum install --disablerepo=* $REPO_CONF -y sfdc-release
		    #yum update --disablerepo=* $REPO_CONF -y sfdc-release
		    #REPO_CONF="--enablerepo=prodinfra*,rhel-6-*"
                    #check_exit "sfdc-release install"
    			#fi
                case $RH_VER_MAJOR in
                5)
                        case $RH_VER_MINOR in
                        3|5|7|10)
                                POPT_CHECK=`rpm -qa popt | grep 7.2`
                                if [ "$POPT_CHECK" == "popt-1.10.2.3-22.el5_7.2" ]; then

                                    $YUM -y --disablerepo=* $REPO_CONF $EXCLUDES --exclude=popt\* --exclude=kudzu\* update

                                    check_exit "yum update in do_rhel_update"
                                 else
					                $YUM -y --disablerepo=* $REPO_CONF $EXCLUDES --exclude=kudzu\* update
                                    check_exit "yum update in do_rhel_update"
                                fi
                                #yum -y --disablerepo=* --enablerepo=kernel update kernel
                                #yum -y --disablerepo=* --enablerepo=rhel_updates update
                                ;;
                        11)
                                $YUM -y  --disablerepo=* $REPO_CONF $EXCLUDES --exclude=kudzu\* update

                                check_exit "yum update in do_rhel_update"
                                ;;
                        *)
                                echo "Not a supported upgrade"
                                ;;
                        esac
                ;;
                6)
                        case $RH_VER_MINOR in
                        0|2|5)
                                $YUM -y  --disablerepo=* $REPO_CONF $EXCLUDES --exclude=sfdc-release\* update
                                check_exit "yum update in do_rhel_update"
                                $YUM -y  --disablerepo=* $REPO_CONF update sfdc-release
                                check_exit "yum update sfdc-release in do_rhel_update"
                                ;;
                        6|7|8|9)

                                $YUM -y  --disablerepo=* $REPO_CONF --exclude=sfdc-release\* update
                                check_exit "yum update in do_rhel_update"
                                $YUM -y  --disablerepo=* $REPO_CONF update sfdc-release
                                check_exit "yum update sfdc-release in do_rhel_update"
                                ;;
                        *)
                                echo "Not a supported upgrade"
                                ;;
                        esac
                ;;

                7)
                        case $RH_VER_MINOR in
                        *)
                                $YUM -y  --disablerepo=* $REPO_CONF --exclude=sfdc-release\* update
                                check_exit "yum update in do_rhel_update"
                                $YUM -y  --disablerepo=* $REPO_CONF update sfdc-release
                                check_exit "yum update sfdc-release in do_rhel_update"
                                ;;
                        esac
                ;;
                esac
        fi
        if [ $? -eq 0 ]; then
                echo "[$HOSTNAME]:YUM updated the system successfully"
                # W-3910323 - remove vendor repo files
                if [ -f /etc/yum.repos.d/CentOS-Base.repo ]; then
                        echo "Removing 'CentOS' repo files installed as part of centos-release update"
                        rm /etc/yum.repos.d/CentOS*
                fi
                OLD_VERS=`uname -r`
                if [ "$RH_VER_MAJOR" == "6" -a ! -z "$GRUB_CONF" ]
                then 
                	NEW_VERS=`grep title ${GRUB_CONF} | head -1 | awk '{print $3}'`
                	RH_VER=`cat /etc/redhat-release |awk '{print $3}'`
                elif [ "$RH_VER_MAJOR" == "7" -a ! -z "$GRUB_CONF" ]
                then 
                	NEW_VERS=`grep "CentOS Linux" ${GRUB_CONF} | head -1 | awk '{print $4}'`
                	RH_VER=`cat /etc/centos-release | awk '{print $4}'`
                fi
                if [ $TEST_MODE ]; then
                        echo "Test Mode: echo \"[`date`] [$SUDO_USERID] [$HOSTNAME] [kernel updated from {$OLD_VERS} to {$NEW_VERS}] and system updated to {$RH_VER}\" >> $LOGFILE"
                else
                        echo "[`date`] [$SUDO_USERID] [$HOSTNAME] [kernel updated from {$OLD_VERS} to {$NEW_VERS}] and system updated to {$RH_VER}" >> $LOGFILE
                fi
                katExit
        else
                katExit
                do_exit "yum failed to update the system" "TOOLS"
        fi
}

function check_sparc_firmware {

# for sun4v type (T2000, T5xxx, T3, T4), confirm firmware is not so old
# (<= 2007 - 6.4.6) that it will panic with the current kernel
# good firmware will show version in prtdiag, so absence will be treated
# as indication it's too old.

  echo "Checking system firmware on sun4v system to ensure no compatibility issues."
  FIRMWARE=`/usr/platform/\`uname -i\`/sbin/prtdiag -v |grep "System Firmware"`
  if [ -z "$FIRMWARE" ]; then
    echo "No firmware version info found using prtdiag.  It is highly likely"
    echo "that this system's firmware predates 6.4.6 and must be upgraded"
    echo "before it can be patched.  Consult following doc for instructions:"
    echo "https://docs.google.com/a/salesforce.com/document/d/1COCpBrmKYnNRLQx5_QSMHlpmHx8njnyDp80sXEvJDxM/edit"
    do_exit "Firmware incompatible with kernel" "UNSUPPORTED"
  else
    echo "Firmware level identied: safe to proceed with patching"
    echo $FIRMWARE
  fi
}

function determine_solaris_method {

# determine patching method based on patchset version
# default is "full".  user can specify the Candidate patchset with -c
# "short" is no longer an option

  HOST_VERSION=`grep patchcluster-version /etc/sfdc-install | awk '{print $2}'`
  PATCHSET_VERSION=`awk '/DATE: /{print $2}' ${PATCHDIR}/${PATCHSET_README}`
  dprint "HOST_VERSION: ${HOST_VERSION}"
  dprint "PATCHSET_VERSION: ${PATCHSET_VERSION}"

  echo ${HOST_VERSION} | grep '[a-zA-Z]' > /dev/null
  RES=$?
  if [ $RES = "0" ]; then
    # contains letters, ie May/13/08.  this date version is deprecated
    # so assume that patchset version is way old
    HOST_VERSION_INT=19700101
  else
    HOST_VERSION_INT=`echo ${HOST_VERSION} | tr -d "."`
  fi

  PATCHSET_VERSION_INT=`echo ${PATCHSET_VERSION} | tr -d "."`

  dprint "HOST_VERSION_INT: ${HOST_VERSION_INT}"
  dprint "PATCHSET_VERSION_INT: ${PATCHSET_VERSION_INT}"

  if [ ${HOST_VERSION_INT} -ge ${PATCHSET_VERSION_INT} ]; then
    METHOD=none
  else
    METHOD=full
  fi

  # allow user to force (re)install even if at current patchset version
  if [ ${FORCE} = "1" ]; then
    METHOD=full
  fi

  # this is an example of bash's shortcomings as a scripting language
  # poor support for floats, so we'll convert kernel into big int
  OSVERSIONINT=`echo $OSVERSION |tr -d "-" |bc`

  if [ ${OSVERSIONINT} -le 11885536 ]; then
    METHOD=too_old
  fi
}

function mount_solaris_patches {

  if [ "$1" == "mount" ]; then

  # check nfs client service, which is not on by default on solaris
  # the failure mechanisms here may need refinement based on experience
    STATUS=`svcs -H network/nfs/client |awk '{print $1}'`
    if [ $STATUS != "online" ]; then
      /usr/sbin/svcadm enable -r network/nfs/client
      sleep 2
      STATUS=`svcs -H network/nfs/client |awk '{print $1}'`
      if [ $STATUS != "online" ]; then
        echo "Failed in attempt to online nfs client services"
        exit 5
      fi
    fi

    INSTALL=/export/install
    INST_HOST=ops-inst2-1-${SITECODE}.${DNS_DOMAIN}

    if [ $REPO_OVERRIDE ]; then
      echo "Using supplied nfs mount of $REPO_OVERRIDE instead of ${INST_HOST}:${INSTALL}"
      /usr/sbin/mount $REPO_OVERRIDE /mnt
    else
      dprint "Mounting ${INST_HOST}:${INSTALL} /mnt"
      /usr/sbin/mount ${INST_HOST}:${INSTALL} /mnt
    fi

    if [ $? = 0 ]; then
      UMOUNT="yes"
      # a lot of hosts have this already mounted, don't presume it's inactive
    elif [ -d $PATCHDIR ]; then
      UMOUNT="no"
      echo "ops-inst mount already present on host.  Ignore error."
    else
      echo "Error mounting $INSTALL to /mnt.  Unmount existing mount and re-run $0."
      exit 5
    fi

  elif [ "$1" == "unmount" ]; then
    if [ "$UMOUNT" == "yes" ]; then
      cd /
      dprint "Unmounting /mnt"
      /usr/sbin/umount -f /mnt
    else
      echo "Mount point was already present, not unmounting."
    fi

  fi
}

function do_solaris_update {

  # Symlink the patch dirs as follows:
  # ops-inst1-1-sfz:/export/install/sol10/ (or wherever inst master lives)
  # 10_Recommended --> 10_Recommended_CPU_2013-04 (tested CPU)
  # 10_x86_Recommended --> 10_x86_Recommended_CPU_2013-04 (tested CPU)
  # 10_Recommended_Candidate --> 10_Recommended_CPU_2013-07 (latest CPU)
  # 10_x86_Recommended_Candidate --> 10_x86_Recommended_CPU_2013-07 (latest CPU)
  # "Candidate" patchset is intended for ie PerfEng testing

  if [ $OSTYPE = "SOLARIS-X86" ]; then
    if [ ${METHOD} = "candidate" ]; then
      PATCHNAME=10_x86_Recommended_Candidate
    else
      PATCHNAME=10_x86_Recommended
    fi
    PATCHSET_README=10_x86_Recommended*README
  elif [ $OSTYPE = "SOLARIS-SPARC" ]; then
    if [ ${METHOD} = "candidate" ]; then
      PATCHNAME=10_Recommended_Candidate
    else
      PATCHNAME=10_Recommended
    fi
    PATCHSET_README=10_Recommended*README
  fi

  PATCHDIR=/mnt/sol10/${PATCHNAME}
  dprint "PATCHNAME: $PATCHNAME"
  dprint "PATCHDIR: $PATCHDIR"
  dprint "PATCHSET_README: $PATCHSET_README"

  mount_solaris_patches mount

  determine_solaris_method

  if [ ${METHOD} = "none" ]; then
    mount_solaris_patches unmount
    do_exit "Host already has current patchset: ${PATCHSET_VERSION}" "NOOP"
  elif [ ${METHOD} = "full" ]; then
    echo "Installing patchset ${PATCHSET_VERSION}."
    if [ $TEST_MODE ]; then
      echo "Test Mode:  cd $PATCHDIR"
      echo "Test Mode:  ./installpatchset --s10patchset"
      RES=0    # fake $RES for below
    else
      cd $PATCHDIR
      ./installpatchset --s10patchset
      RES=$?
    fi

    # sometimes /etc/mail/sendmail.cf gets clobbered by patches; regenerate
    SM_COMMON=sendmail-common.mc
    if [ $TEST_MODE ]; then
      echo "Test Mode: Regenerating sendmail.cf from $SM_COMMON"
      echo "Test Mode: Regenerating sendmail.cf from $SM_COMMON" >> $LOGFILE
    else
      if [ -f /mnt/sol10/sysfiles/$SM_COMMON ]; then
        echo "Regenerating sendmail.cf from $SM_COMMON"
        echo "Regenerating sendmail.cf from $SM_COMMON" >> $LOGFILE
        cp /mnt/sol10/sysfiles/$SM_COMMON /etc/mail/cf/cf/
        perl -w -i -p -e "s/SETBYSCRIPT/${SITECODE}/g" /etc/mail/cf/cf/$SM_COMMON
        cd /etc/mail/cf/cf && /usr/ccs/bin/m4 ../m4/cf.m4 $SM_COMMON > /etc/mail/sendmail.cf
      else
        echo "Can't find $SM_COMMON, please confirm sendmail works."
        echo "Can't find $SM_COMMON, please confirm sendmail works." >> $LOGFILE
      fi
    fi

  elif [ ${METHOD} = "too_old" ]; then
    mount_solaris_patches unmount
    do_exit "Host kernel version too old for one pass update: $OSVERSIONINT.  Reimage host" "UNSUPPORTED"
  else
    mount_solaris_patches unmount
    do_exit "Unknown install method: ${METHOD}" "NOOP"
  fi

  mount_solaris_patches unmount

  if [ ${RES} = "0" ]; then
    echo "Patching completed successfully."
    OLD_VERS=$OSVERSION
    NEW_VERS=`uname -v |cut -f2 -d_`
  else
    do_exit "There were errors installing the patchset.  Verify host." "TOOLS"
  fi

  if [ $TEST_MODE ]; then
    echo "Test Mode: echo \"[`date`] [$SUDO_USERID] [$HOSTNAME] [kernel updated from {$OLD_VERS} to {$NEW_VERS}]\" >> $LOGFILE"
    echo "Test Mode: (updating /etc/sfdc-install)"
  else
    echo "[`date`] [$SUDO_USERID] [$HOSTNAME] [kernel updated from {$OLD_VERS} to {$NEW_VERS}]" >> $LOGFILE
    TMP_SI=`mktemp /var/tmp/sfdc-install.XXXXXX`
    sed -e "s/patchcluster-version .*/patchcluster-version ${PATCHSET_VERSION}/" /etc/sfdc-install > ${TMP_SI}
    mv ${TMP_SI} /etc/sfdc-install
    chmod 644 /etc/sfdc-install
  fi
}


function do_fix_hald {
        echo '--child-timeout=600' >> /etc/sysconfig/haldaemon
}

function do_turnoff_services {

#-----Services Off-----
echo "Turning off unwanted services"
echo "Some might print warnings if they're not installed.  No worries."

for SERVICE in \
gpm kudzu audit auditd iptables ip6tables nfslock rhnsd \
pcmcia arptables_jf anacron rpcgssd cpuspeed \
readahead readahead_early hpoj apmd canna FreeWnn xfs cups \
firstboot pcscd readahead_later yum-updatesd avahi-daemon \
avahi-dnsconfd jexec mcstrans restorecond rpcidmapd \
netfs cpuspeed bnx2id iscsi iscsid
do
    if /sbin/chkconfig --list $SERVICE >/dev/null 2>&1; then
        /sbin/chkconfig --level 0123456 $SERVICE off
        /sbin/chkconfig --del $SERVICE
    fi
done
# ---- turn netfs back on for dev hosts in SFM/CRD/PRD that use it ------
if [ $SITECODE == "sfm" ] || [ $SITECODE == "crd" ] || [ $SITECODE == "prd" ]; then
    if grep "nfs" /etc/fstab >/dev/null; then
        /sbin/chkconfig --add netfs
        /sbin/chkconfig --level 345 netfs on
    fi
fi

}

function do_oracleasm_update {

                #check for valid sfdc-mgmt-oracle.repo
        yumsfdcoraclemgmtrepofile=/etc/yum.repos.d/sfdc-oracle-mgmt.repo

        if [ ! -f $yumsfdcoraclemgmtrepofile ];then
                echo "Creating sfdc-oracle-mgmt repo file"
        cat > $yumsfdcoraclemgmtrepofile << EOF
[sfdc-oracle-mgmt]
name=SFDC Oracle Management Repository
baseurl=http://ops-inst1-1-$SITECODE.ops.sfdc.net/sfdc-oracle-mgmt/x86_64/${RH_VER_MAJOR}Server
        http://ops-inst2-1-$SITECODE.ops.sfdc.net/sfdc-oracle-mgmt/x86_64/${RH_VER_MAJOR}Server
enabled=0
gpgcheck=0

EOF
        fi
        echo "Updating oracle asm"
        yum -y --enablerepo=rhel_updates install oracleasm
        yum -y --enablerepo=sfdc-oracle-mgmt update
        yum -y --enablerepo=sfdc-oracle-mgmt remove oracleasm-$(uname -r)

}

function do_remove_public_oel_yum {
        if [ -r /etc/yum.repos.d/public-yum-ol6.repo ]; then
           echo "Removing /etc/yum.repos.d/public-yum-ol6.repo file"
           rm /etc/yum.repos.d/public-yum-ol6.repo
        fi
}

function do_uek_update {
        echo "Updating UEK kernel"
        $YUM -y  --disablerepo=* $REPO_CONF --exclude=sfdc-release\* --enablerepo=*uek* update kernel-uek.x86_64
}

function do_host_update {
        if [ $OSTYPE == "RHEL" ] || [ $OSTYPE == "CENTOS" ]; then
                do_kernel_cleanup
		        cleanup_stale_initramfs
                do_rhel_update
                do_turnoff_services
                fix_zshrc_prompt
                do_fix_ramfs
                case $HOSTFUNC in
                   cmsdb|trustdb|sbdb|dbtest|dgdb|webproddb|webdb|webstgdb|*db)
                   		if [ $OSTYPE == "RHEL" ];then
                        	do_oracleasm_update
                        fi
                        do_rc_sysinit_fix
                        do_fix_hald
                   ;;
		   ffx)
			add_ffx_snmp
		   ;;
                   *)
                        echo "Not a DB host so nothing to do"
                   ;;
                esac
                if [ $do_reboot == "1" ]; then
                  reboot_host
                fi
        elif [ $OSTYPE == "OEL" ]; then
                do_rhel_update
                fix_zshrc_prompt
                do_remove_public_oel_yum
                do_uek_update
                case $HOSTFUNC in
                   *db|db*)
                      #do_oracleasm_update
		      # Empty for now
                   ;;
                   *)
                      echo "Not a DB host so nothing to do"
                   ;;
                esac
                if [ $do_reboot == "1" ]; then
                  reboot_host
                fi
        elif [ $OSTYPE == "SOLARIS-X86" ] || [ $OSTYPE == "SOLARIS-SPARC" ]; then
                do_solaris_update
                if [ $do_reboot -eq 1 ]; then
                  reboot_host
                fi
        else
                do_exit "Unable to update and reboot OS [$OSTYPE]" "UNSUPPORTED"
        fi
}

function reboot_host {
        if [ $OSTYPE == "RHEL" ] || [ $OSTYPE == "OEL" ] || [ $OSTYPE == "CENTOS" ] ; then
                if [ $warn_and_wait -gt 0 ]; then
                        if [ $TEST_MODE ]; then
                                echo "Test Mode: shutdown -r +$warn_and_wait \"The kernel and system were updated and node $HOSTNAME needs to be rebooted\""
                        else
                                /sbin/shutdown -r +$warn_and_wait "The kernel and system were updated and node $HOSTNAME needs to be rebooted"
                        fi
                else
                        if [ $TEST_MODE ]; then
                                echo "Test Mode: echo \"[`date`] [$SUDO_USERID] [$HOSTNAME] [kernel updated from {$OLD_VERS} to {$NEW_VERS}]\" >> $LOGFILE"
                                echo "Test Mode: /usr/bin/reboot"
                        else
                                echo "[`date`] [$SUDO_USERID] [$HOSTNAME] [kernel updated from {$OLD_VERS} to {$NEW_VERS}]" >> $LOGFILE
                                $REBOOT
                        fi
                fi
        elif [ $OSTYPE == "SOLARIS-X86" ] || [ $OSTYPE == "SOLARIS-SPARC" ]; then
                if [ $TEST_MODE ]; then
                        echo "Test Mode: bootadm update-archive"
                        echo "Test Mode: bootadm update-archive" >> $LOGFILE
                else
                        echo "[`date`] [$SUDO_USERID] [$HOSTNAME] [bootadm update-archive]" >> $LOGFILE
                        /sbin/bootadm update-archive -f
                        sleep 30
                fi

                if [ $warn_and_wait -gt 0 ]; then
                        # Solaris uses seconds, not minutes for shutdown wait
                        wait=`echo "$warn_and_wait * 60" |bc`
                        if [ $TEST_MODE ]; then
                                echo "Test Mode: shutdown -i6 -y -g$wait \"The kernel was updated and node $HOSTNAME needs to be rebooted\""
                        else
                                /etc/shutdown -i6 -y -g$wait "The kernel was updated and node $HOSTNAME needs to be rebooted"
                        fi
                else
                        if [ $TEST_MODE ]; then
                                echo "Test Mode: $REBOOT"
                        else
                                echo "[`date`] [$SUDO_USERID] [$HOSTNAME] [kernel updated from {$OLD_VER} to {$NEW_VERS}]" >> $LOGFILE
                                $REBOOT
                        fi
                fi
        else
                echo "Don't know how to reboot the host"
                exit 1
        fi
}

function gen_alt_repo {
    ver=$1
    repo="http://ops-inst1-1-$SITECODE.ops.sfdc.net/media/rhel_kernel_update/$OSVERSION"
    echo "$repo $ver"

    ensure_valid_yum_config $repo $ver

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
        echo "  -b              use katello (bypass by default)"
        echo "  -d              run with debug output"
        echo "  -f              [Sun] force (re)install of patchset"
        echo "  -c              [Sun] install 10_Recommended Candidate patchset"
        echo "  -h              print help and exit"
        echo "  -a              candidate repo to use"
        echo "  -p              confirms ok to patch production hosts 'Deprecated Don't use"
        echo "  -r <repo_url>   use separate <repo_url> as the location of the kernel package repository"
        echo "  -s              only configure the repository and check if there are pending updates, but do not apply them or reboot the machine"
        echo "  -t              run in test mode, where changes are echoed but not executed"
        echo "  -w <min>        reboot the machine, and warn all users on the machine that it will be rebooted in <min> minutes"
        echo "  -e              reboot the machine"
        echo "  -q               run in quiet mode"
}

function main {
        warn_and_wait=0
        while getopts "dfcbqhpra:stw:e" OPTION; do
                case $OPTION in
                        b)
                                USE_KAT=true
                                ;;
                        d)
                                export KERNEL_UPDATE_DEBUG=1
                                ;;
                        f)
                                export FORCE=1
                                ;;
                        c)
                                export METHOD=candidate
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
            if [ "$USE_KAT" == "true" ]; then
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