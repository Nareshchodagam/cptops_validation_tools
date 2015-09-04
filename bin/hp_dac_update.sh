#!/bin/bash

SHORT_HOST=$(hostname | cut -d. -f1)
SITE=`hostname | cut -d'.' -f1 | cut -d- -f4`
MOUNTPOINT='/mnt'
INSTSERVER="ops-inst1-1-$SITE"

HPSUM=/mnt/temp/HP/utilities/SPP/SPP201409/hp/swpackages/hpsum
UPDATE_DIR=/mnt/common/firmware/HP/PERC


errCheck(){
        if [ $? != 0 ]
        then
                echo "FOUND ERROR: Exiting"
                exit 2
        fi
}

if mount | grep $INSTSERVER;
then
        echo -en "$INSTSERVER already mounted on $MOUNTPOINT\n"
else
        /bin/mount ${INSTSERVER}:/export/install ${MOUNTPOINT}
        errCheck
fi

HPSSA_DIR=/mnt/temp/HP/utilities/SPP/SPP201409/hp/swpackages

# Install hpssacli if necessary
if [ ! -x /usr/sbin/hpssacli ]; then
    rpm -ivh $HPSSA_DIR/hpssa-2.0-23.0.x86_64.rpm $HPSSA_DIR/hpssacli-2.0-23.0.x86_64.rpm
fi

CURRENT_VER=$(hpssacli ctrl all show config detail | egrep '^\s\s\sFirmware\sVersion: ' | cut -d' ' -f6)
TARGET_VER="6.34"

# Update file is for firmware version 6.34 for HP P420i drive array controllers
UPDATE_FILE='CP026358.scexe'

# Set boot order to HDD
/sbin/hpbootcfg -H
errCheck

# Clear out log directory
if [ -d /var/hp/log ]; then
    rm -rf /var/hp/log/*
fi

# Apply update if necessary
if [ bc <<< "$CURRENT_VER<$TARGET_VER" ]; then
    echo "$SHORT_HOST: Current Firmware = $CURRENT_VER | Target Firmware = $TARGET_VER"
    $HPSUM -veryv -s -f:rom -use_location $UPDATE_DIR -c $UPDATE_FILE
    errCheck
else
    echo "Host $SHORT_HOST already at $CURRENT_VER. No need to patch."
fi

grep 'Success, reboot required' /var/hp/log/localhost/hpsum_log.txt || {
    echo "ERROR: $(hostname) - the update was not installed correctly"
    exit 2
}

if mount | grep $INSTSERVER;
then
    /bin/umount ${MOUNTPOINT}
    errCheck
fi