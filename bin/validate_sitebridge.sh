# Sitebridge service validation script
# Cillian Gallagher 01Nov18

SERV2CHK=sitebridge-bootstrapper
CHECK_SVC=$(systemctl is-active --quiet $SERV2CHK); RETVAL=$?

if [ ${RETVAL} -eq 0 ]
        then
        echo "$SERV2CHK Processes:        [RUNNING]"
else
        echo "ERROR $SERV2CHK Processes:        [NOT RUNNING]"
        exit 1
fi
