#!/bin/bash
#$Id: validate_smsapi.sh 2018-06-11 ye.hong@salesforce.com $

PYTHON="/opt/sfdc/python27/bin/python"
TESTSCRIPT="/opt/app/sms_ops_scripts/test_smsapi.py"
ROLE="smsapidev"
HOSTNAME=$(hostname)
PORT=8443

TEST_COMMAND="$PYTHON $TESTSCRIPT -r $ROLE -s $HOSTNAME:$PORT"
OUTPUT=$( $TEST_COMMAND )
RETURN_CODE=$?

exit $RETRUN_CODE