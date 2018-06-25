#!/usr/bin/env bash

#
# This shell script is used to verify DB connection from dbextract hosts.
#


while getopts ":d:h" opt; do
    case ${opt} in
    d )
    DC=$OPTARG
    ;;
    h )
    echo "Usage: "
    echo "  cmd -h      Display help message"
    echo "  cmd -d      Check DB connectivity on given DC"
    exit 0
    ;;
    * ) echo "Invalid option"
    exit 1
    ;;
    esac
done



# Variables
RUNUSER='/sbin/runuser'
TNSFILE='/etc/tnsnames.ora'
USER='sfdc_ops'
DB_NAME=$(grep -i service_name $TNSFILE | grep -i $DC | awk -F[=\)] "{print \$2}" | egrep -i 'EU|AP|NA' | tail -1) ; RETVAL_DBNAME=$?
echo $DC


if [ -f ${TNSFILE} ] ; then
    if [ ${RETVAL_DBNAME} -eq 0 ]; then
        $RUNUSER -l $USER -p -c "source .bashrc && tnsping $DB_NAME"
    else
        echo "Can't find DB NAME"
        exit 1
    fi
else
    echo "Can't find tnsnames.ora file"
    exit 1

fi
