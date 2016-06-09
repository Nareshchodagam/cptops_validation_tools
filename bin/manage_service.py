#!/usr/bin/python
#
# manage_service.py
#
""" Record current state of a process and stop/start as necessary"""

import logging
import os
import commands
from optparse import OptionParser
import subprocess
import sys

tmpDir='/tmp/'

def recordStatus(procName,procString):
    logging.debug('Checking for running process' + procName)
    output=commands.getoutput('ps -ef | grep -v grep | grep -v python | grep -v sudo | grep "' + procString + '"' )
    logging.debug('Result: ' + output)
    tmpFile=tmpDir + procName + '_status.tmp'

    if procName in output:
        print(procName + " is currently running")
        logging.debug('Printing RUNNING status to ' + tmpFile)
        status='RUNNING'
    else:
        print(procName + " is NOT currently running")
        logging.debug('Printing NOT_RUNNING status to ' + tmpFile)
        status='NOT_RUNNING'

    try:
        f=open(tmpFile,'w')
        f.write(status)
        f.close()
    except:
        print('Unable to write to file: ' + tmpFile)
        exit(1)

    return status

def getStatus(procName):
    logging.debug('Retrieving status for process ' + procName)
    tmpFile=tmpDir + procName + '_status.tmp'
    try:
        f=open(tmpFile,'r')
        svcStatus=f.readline()
        print('Recorded status for ' + procName + ' is ' + svcStatus)
        f.close()
    except:
        print('Unable to read file: ' + tmpFile)
        print('The service state must be recorded. Run: ')
        print('manage_service.py -n ' + procName + ' -r')
        exit(1)
    return svcStatus

def startService(procName,cmd,force):
    status=getStatus(procName)
    if status.strip() == "RUNNING" or force is True:
        print('Starting service: ' + procName)
        try:
            output=commands.getoutput(cmd)
            logging.debug(output)
            logging.debug('Removing tmpfile after service start.')
            os.remove(tmpDir + procName + '_status.tmp')
        except:
            print('Unable to execute: ' + cmd)
            exit(1)
    else:
        print('Refusing to start service as it was not recorded running')
        print('Run with the -f (force) option to override this')

def stopService(procName,procString,cmd,force):
    status=recordStatus(procName,procString)
    if status.strip() == "RUNNING" or force is True:
        print('Stopping process: ' + procName)
        try:
            output=commands.getoutput(cmd)
            logging.debug(output)
        except:
            print('Unable to execute: ' + cmd)
            exit(1)
    else:
        print('Process is not running. Nothing to stop.')
        
if __name__ == "__main__":

    usage="""

    %prog
    ------------------------------------------------------------------------

    Record the current status of a process:
    %prog -n focus -r

    Retreive the last recorded state of a process:
    %prog -n focus -g

    Start a service:
    %prog -n focus -c /opt/sr-tools/focus/tomcat/bin/startup.sh -s

    Force start a service:
    %prog -n focus -c /opt/sr-tools/focus/tomcat/bin/startup.sh -s -f

    Stop a service:
    %prog -n focus -c /opt/sr-tools/focus/tomcat/bin/shutdown.sh -k

    Force stop a service:
    %prog -n focus -c /opt/sr-tools/focus/tomcat/bin/shutdown.sh -k -f

    ------------------------------------------------------------------------

    """

    parser = OptionParser(usage)
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="Verbosity")
    parser.add_option("-r", action="store_true", dest="checksvc", default=False, help="Record process state")
    parser.add_option("-g", action="store_true", dest="getstatus", default=False, help="Get last status")
    parser.add_option("-s", action="store_true", dest="startsvc", default=False, help="Start Process")
    parser.add_option("-k", action="store_true", dest="stopsvc", default=False, help="Stop Process")
    parser.add_option("-n", dest="procname", help="Process Name")
    parser.add_option("-e", dest='extended_proc_name', default=False, help='Extended process name')
    parser.add_option("-f", action="store_true", dest="force", default=False, help="Force")
    parser.add_option("-c", dest="cmd", help="Command")

    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if options.extended_proc_name:
        procname=options.procname
        procstring=options.extended_proc_name
    else:
        procname=options.procname
        procstring=options.procname
            
    if options.checksvc:
        recordStatus(procname,procstring)

    if options.getstatus:
        result=getStatus(procname)
        print "RESULT: " + result

    if options.startsvc:
        startService(procname,options.cmd,options.force)

    if options.stopsvc:
        stopService(procname,procstring,options.cmd,options.force)
