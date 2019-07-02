#!/usr/bin/python
# manage_service.py
#
""" Record current state of a process and stop/start as necessary"""

import logging
import platform
import os
import subprocess
import commands
from optparse import OptionParser
import subprocess
import shlex
import sys

tmpDir='~'

def recordStatus(procName, procString):
    proc_cmd = 'ps -ef | egrep -v "grep|python|sudo" | grep "' + procString + '"'
    tmpFile = tmpDir + procName + '_status.tmp'
    logging.debug('Checking for running process' + procName)
    if options.sysinit:
        if "centos" in os.lower() and ver[0] == 7:
            proc_initcmd = "systemctl status %s" % procName
        else:
            proc_initcmd = "service %s status" % procName
        retcode = subprocess.call(shlex.split(proc_initcmd))
        if retcode == 0:
            print(procName + " is currently running\n")
            logging.debug('Printing RUNNING status to ' + tmpFile)
            status = 'RUNNING'
        else:
            print(procName + " is NOT currently running\n")
            logging.debug('Printing NOT_RUNNING status to ' + tmpFile)
            status = 'NOT_RUNNING'
    else:
        output=commands.getoutput(proc_cmd)
        if procName in output:
            print(procName + " is currently running\n")
            logging.debug('Printing RUNNING status to ' + tmpFile)
            status = 'RUNNING'
        else:
            print(procName + " is NOT currently running\n")
            logging.debug('Printing NOT_RUNNING status to ' + tmpFile)
            status = 'NOT_RUNNING'

    try:
        f = open(tmpFile,'w')
        f.write(status)
        f.close()
    except:
        print('Unable to write to file: ' + tmpFile)
        exit(1)

    return status

def getStatus(procName):
    logging.debug('Retrieving status for process ' + procName)
    tmpFile = tmpDir + procName + '_status.tmp'
    try:
        f = open(tmpFile,'r')
        svcStatus = f.readline()
        print('Recorded status for ' + procName + ' is ' + svcStatus)
        f.close()
    except:
        print('Unable to read file: ' + tmpFile)
        print('The service state must be recorded. Run: ')
        print('manage_service.py -n ' + procName + ' -r')
        exit(1)

    return svcStatus

def serviceStatus(procName):
    status = chkInitState(procName)
    if status == 0:
        print(procName + " is running")
    else:
        print(procName + " is not running")
        exit(1)

def chkInitState(procName):
    logging.debug('Checking current status for process ' + procName)
    if "centos" in os.lower() and ver[0] == 7:
        proc_initcmd = "systemctl status %s" % procName
    else:
        proc_initcmd = "service %s status" % procName
    retcode = subprocess.call(shlex.split(proc_initcmd))

    return retcode

def startService(procName, cmd, force):
    status=getStatus(procName)
    rm_cmd = "rm %s%s_status.tmp" % (tmpDir, procName)
    if status.strip() == "RUNNING" or force is True:
        if options.sysinit:
            retcode = chkInitState(procName)
            if retcode == 0:
                print "%s Process already running..." % procName
                return
        print('Starting service: ' + procName)
        for procCmd in cmd, rm_cmd:
            retcode = subprocess.call(shlex.split(procCmd))
            if retcode != 0:
                logging.error("Problem executing %s", procCmd)
    else:
        print('Refusing to start service as it was not recorded running')
        print('Run with the -f (force) option to override this')

def stopService(procName, procString, cmd, force, sysinit):
    status = recordStatus(procName, procString)
    if status.strip() == "RUNNING" or force is True:
        print('Stopping process: ' + procName)
        try:
            print cmd
            output = commands.getoutput(cmd)
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
    %prog -n focus -r -i *Process controlled by init.

    Retreive the last recorded state of a process:
    %prog -n focus -g
    
    Check the status:
    %prog -n focus -a
    
    Start a service:
    %prog -n focus -c /opt/sr-tools/focus/tomcat/bin/startup.sh -s

    %prog -n focus -i -s *Process controlled by init.

    Force start a service:
    %prog -n focus -c /opt/sr-tools/focus/tomcat/bin/startup.sh -s -f

    %prog -n focus -i -s -f *Process controlled by init.

    Stop a service:
    %prog -n focus -c /opt/sr-tools/focus/tomcat/bin/shutdown.sh -k

    %prog -n focus -k -i *Process controlled by init.

    Force stop a service:
    %prog -n focus -c /opt/sr-tools/focus/tomcat/bin/shutdown.sh -k -f

    %prog -n focus -i -k -f *Process controlled by init.


    ------------------------------------------------------------------------

    """

    parser = OptionParser(usage)
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="Verbosity")
    parser.add_option("-r", action="store_true", dest="checksvc", default=False, help="Record process state")
    parser.add_option("-i", action="store_true", dest="sysinit", default=False, help="Process is controlled by init.")
    parser.add_option("-g", action="store_true", dest="getstatus", default=False, help="Get last status")
    parser.add_option("-a", action="store_true", dest="checkstatus", default=False, help="check status")
    parser.add_option("-s", action="store_true", dest="startsvc", default=False, help="Start Process")
    parser.add_option("-k", action="store_true", dest="stopsvc", default=False, help="Stop Process")
    parser.add_option("-n", dest="procname", help="Process Name")
    parser.add_option("-e", dest='extended_proc_name', default=False, help='Extended process name')
    parser.add_option("-f", action="store_true", dest="force", default=False, help="Force")
    parser.add_option("-c", dest="cmd", help="Command")

    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    os, ver, stg = platform.linux_distribution()

    proc_lst = options.procname.split(',')
    for procs in proc_lst:
        if options.extended_proc_name:
            procname = procs
            #procname = options.procname
            procstring = options.extended_proc_name
        else:
            procname = procs
            procstring=procs
    
        if options.checksvc:
            recordStatus(procname, procstring)
    
        if options.getstatus:
            result = getStatus(procname)
            print "RESULT: " + result

        if options.checkstatus:
            serviceStatus(procname)

        if options.startsvc and options.sysinit:
                if "centos" in os.lower() and ver[0] == 7:
                   cmd = "systemctl start %s" % procname
                else:
                   cmd = "service %s start" % procname
                startService(procname, cmd, options.force)
        elif options.startsvc and not options.sysinit:
            startService(procname, options.cmd, options.force)
        if options.stopsvc and options.sysinit:
                if "centos" in os.lower() and ver[0] == 7:
                   cmd = "systemctl stop %s" % procname
                else:
                   cmd = "service %s stop" % procname
                stopService(procname, procstring, cmd, options.force, options.sysinit)
        elif options.stopsvc and not options.sysinit:
            stopService(procname, procstring, options.cmd, options.force, options.sysinit)
