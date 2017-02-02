#!/usr/bin/python
"""Script to validate which os is being worked on"""

#from datetime import datetime, date, timedelta
import sys
import re
import subprocess
import logging
from optparse import OptionParser
#import glob
#import json
import os.path
import platform

def whichArch():
    return platform.system()

def whichOS():
    os_types = {'oel': '/etc/oracle-release', 'rhel': '/etc/redhat-release', 'centos': '/etc/centos-release'}
    os_type = ''
    if os.path.isfile(os_types['oel']):
        os_type = 'OEL'
    elif os.path.isfile(os_types['centos']):
         os_type = 'CENTOS'
    elif os.path.isfile(os_types['rhel']):
         os_type = 'RHEL'
    else:
        os_type = 'UNKNOWN'
    return os_type

def run_cmd(cmdlist):
    logging.debug(cmdlist)
    run_cmd = subprocess.Popen(cmdlist, stdout=subprocess.PIPE)
    out, err = run_cmd.communicate()
    return out




if __name__ == "__main__":
    usage = """
    Validate the hosts OS type.
    
    %prog -t [rhel|centos|oel|solaris] -v
    
    %prog -t rhel
    
    
    """
    parser = OptionParser(usage)
    parser.add_option("-t", dest="ostype", action="store", help="The os type to match")
    parser.add_option("-v", action="store_false", dest="verbose", help="verbosity")
    (options, args) = parser.parse_args()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    if options.ostype:
        arch = whichArch()
        if arch == 'Linux':
            os = whichOS()
            if os == options.ostype.upper():
                print("Checked OS matches host OS : %s : %s" % (os, options.ostype.upper()))
                sys.exit(0)
            else:
                print("Checked OS does not match host OS : %s : %s" % (os, options.ostype.upper()))
                sys.exit(1)
        elif arch == 'SunOs':
            os = 'Solaris'
        else:
            os = 'Unknown'
