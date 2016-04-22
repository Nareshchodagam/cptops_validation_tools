#!/usr/bin/python
"""Script to validate which os is being worked on"""

#from datetime import datetime, date, timedelta
import sys
import re
import subprocess
import logging
from optparse import OptionParser
#import glob
#import common
#import json
import os.path
#import platform
reload(sys)
sys.setdefaultencoding('utf8')

if __name__ == "__main__":
    usage = """
    if checkhosts file does not exist create it  
    if it is there exclude hosts in checkhosts file from list of hosts -H 
    %prog -H [hostlist] -v
    """
     
    parser = OptionParser(usage)
    parser.add_option("-H", dest="hosts", action="store", help="comma separated list of hosts , buildplan v_HOSTS")
    parser.add_option("-v", action="store_true", dest="verbose", help="verbosity")
    (options, args) = parser.parse_args()
    

    def cleanline(line):
        return line.strip()
    if not options.hosts:
       sys.exit(1) 
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    filename =  os.path.expanduser('~') + '/checkhosts'
    excludelist, returnlist = [],[]
    open(filename,'a')

    with open(filename,'r') as f:
        for line in f:
	    excludelist.append(cleanline(line))
    for line in options.hosts.split(','):
        line = cleanline(line)
        if line not in excludelist:
            returnlist.append(line)
            
    logging.debug('Excludelist:') 
    logging.debug(excludelist) 
    logging.debug('Returnlist:') 
    logging.debug(returnlist) 
    
    print ','.join(returnlist)
    #if options.hostlist:
        #if arch == 'Linux':
        #    os = whichOS()
        #    if os == options.ostype.upper():
        #        print("Checked OS matches host OS : %s : %s" % (os, options.ostype.upper()))
        #        sys.exit(0)
        #    else:
        #        print("Checked OS does not match host OS : %s : %s" % (os, options.ostype.upper()))
        #        sys.exit(1)
        #elif arch == 'SunOs':
        #    os = 'Solaris'
        #else:
        #    os = 'Unknown'
