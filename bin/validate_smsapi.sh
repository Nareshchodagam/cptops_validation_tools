#!/bin/bash
#$Id: validate_smsapi.sh 2018-06-11 ye.hong@salesforce.com $

PYTHON="/opt/sfdc/python27/bin/python"
TESTSCRIPT="/opt/app/sms_ops_scripts/test_smsapi.py"
ROLE="smsapi"
HOSTNAME=$(hostname)
PORT=8443

TEST_COMMAND="$PYTHON $TESTSCRIPT -r $ROLE -s $HOSTNAME:$PORT"

if [[ $HOSTNAME == *smsapidev* ]]
then 
    TEST_COMMAND="$PYTHON $TESTSCRIPT -r smsapidev -s $HOSTNAME:$PORT" -c smsapi
else
    TEST_COMMAND="$PYTHON $TESTSCRIPT -r smsapi -s $HOSTNAME:$PORT"
fi

OUTPUT=$( $TEST_COMMAND )
RETURN_CODE=$?
exit $RETRUN_CODE
