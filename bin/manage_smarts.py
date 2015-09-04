#!/usr/bin/python
#
# manage_nms.py
#
""" Manage the nms services ensuring that they are brought up in
the appropriate order"""

import logging
import os
import re
import time
import commands
from optparse import OptionParser

def verifyStatus(chkStatus):
    logging.debug('Ensuring that status is' + chkStatus)
    output=commands.getoutput('sm_service show')
    logging.debug('Result: ' + output)

    for line in output.splitlines():
        result=re.findall('\\b' + chkStatus +'\\b', line, flags=re.IGNORECASE)
        if len(result) < 1:
            print(line)
            print('At least one process is not in ' + chkStatus + ' state!')
            return 1
        else:
            print(line)
    return 0

def startServices():
    try:
        print('Starting smarts services...')
        output2=os.system('sm_service start --all')
        print(output2)
    except:
        print('Unable to start services.')
        exit(1)

def stopServices():
    try:
        brokerstatus=0
        x=0
        print('Killing broker...')
        output=os.system('killall brstart')

        while brokerstatus is 0:
            brokerstatus=os.system('ps -ef | grep brstart | grep -v grep')
            print('Waiting for broker to die...')
            time.sleep(5)
            x+=1
            print('Try ' + str(x) + ' of 10')
            if x > 10:
                print('Broker did not die in a reasonable time.')
                exit(1)

        print('Stopping remaining services')
        output=commands.getoutput('sm_service stop --all')
        x=1
        print('Try ' + str(x) + ' of 10')

        while x < 10:
            print('Waiting for all services to confirm stop')
            returnCode=verifyStatus('NOT RUNNING')

            if returnCode is 1:
                x+=1
                time.sleep(60)
            else:
                return(0)

        logging.debug('Result: ' + output)

    except Exception, e:
        print('Caught Exception {0}'.format(e))
        exit(1)

if __name__ == "__main__":

    usage="""

    %prog
    ------------------------------------------------------------------------

    # Start Services
    %prog -s

    # Stop Services
    %prog -k

    # Verify status
    %prog -g -n RUNNING

    ------------------------------------------------------------------------

    """

    parser = OptionParser(usage)
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="Verbosity")
    parser.add_option("-g", action="store_true", dest="getstatus", default=False, help="Get last status")
    parser.add_option("-s", action="store_true", dest="startsvc", default=False, help="Start Process")
    parser.add_option("-k", action="store_true", dest="stopsvc", default=False, help="Stop Process")
    parser.add_option("-n", dest="status_string", help="Status string")

    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if options.getstatus:
        verifyStatus(options.status_string)

    if options.startsvc:
        startServices()

    if options.stopsvc:
        stopServices()
