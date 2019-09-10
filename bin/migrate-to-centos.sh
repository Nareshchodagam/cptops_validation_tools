#!/bin/bash

## Disable existing repos
# For now, just rhel* repos

FORCE=false
if [ ! -z $1 ]; then
	if [ $1 == "--force" ] || [ $1 == "-f" ]; then
		FORCE=true
	fi

	if [ $1 == "--help "] || [ $1 == "-h" ]; then
		echo "Help: Use -f or --force to run on servers that already have /etc/centos-release"
		exit 0
	fi
fi

if [ -f /etc/centos-release ] && [ $FORCE == "false" ]; then
	echo "This appears to be a CentOS server, exiting"
	exit 0
fi

for i in `ls /etc/yum.repos.d/rhel*.repo`; do
	sed -i.bak "s/enabled=1/enabled=0/g" $i
done

SITECODE=`hostname | awk -F. {'print $1'} | awk -F- {'print $4'}`
INST_URL="ops-inst1-1-$SITECODE"
MEDIA="http://$INST_URL/media/centos60u7_x86-64"
PACKAGES="$MEDIA/Packages"
PATCH_URL="http://$INST_URL/rhel_updates/repos/CE6/2016.06.repo"
VENDOR=`/usr/sbin/dmidecode | grep Vendor | awk '{print $2}'`
if [ "$VENDOR" == "Dell" ]; then
	/bin/mount $INST_URL:/export/install /mnt
	if [ -f /opt/dell/dset/dellsysteminfo.sh ]; then
      cp /mnt/kickstart/pkgs/dell-on-centos.sh /opt/dell/dset/dellsysteminfo.sh
    fi
    /bin/umount /mnt
fi

# Remove old kernels to free space on /boot
package-cleanup --disablerepo=* -y --oldkernels --count=1

# Remove RHN related packages and GPG Keys
yum remove -y rhnlib abrt-plugin-bugzilla redhat-release-notes*
rpm -e --nodeps redhat-release-server-6Server
rpm -e --nodeps redhat-indexhtml
for i in `rpm -qa | grep gpg-pubkey`; do
	rpm --erase $i
done

#Install CentOS repos and GPG Key
# We'll need to track these RPMs and make sure the RPMs don't change.
# THey will change when there is a Minor version update.  yum may get bug fixes as well.
yum clean all
rpm --import $MEDIA/RPM-GPG-KEY-CentOS-6
rpm -ivh $PACKAGES/centos-release-6-7.el6.centos.12.3.x86_64.rpm
rpm -ivh $PACKAGES/centos-indexhtml-6-2.el6.centos.noarch.rpm
rpm -Uvh $PACKAGES/yum-plugin-fastestmirror-1.1.30-30.el6.noarch.rpm
rpm -Uvh $PACKAGES/yum-3.2.29-69.el6.centos.noarch.rpm

# Disable fastest mirror plugin
sed -i.bak "s/enabled=1/enabled=0/g" /etc/yum/pluginconf.d/fastestmirror.conf

# check if subscription-manager exists to avoid a false positive
if ! [ -x "$(subscription-manager)" ]; then
  exit 1
else
  # Remove all RHEL subscriptions and products, but we're not going to register to Katello in this script
  subscription-manager unregister
  subscription-manager remove --all
  subscription-manager clean
  rm -f /etc/pki/product/*.pem > /dev/null
fi

yum -y -c $PATCH_URL clean all
# remove any existing CentOS repos:
rm -f /etc/yum.repos.d/CentOS* > /dev/null
yum -y -c $PATCH_URL reinstall \*
rm -f /etc/yum.repos.d/CentOS* > /dev/null

# Final step should be to patch.  Use system_update.sh in a separate step.
