#!/usr/bin/python
"""script to exclude hosts from a comma separated list"""

#from datetime import datetime, date, timedelta
import sys
import re
import subprocess
import logging
from optparse import OptionParser
#import glob
#import json
import os.path
#import platform
reload(sys)
sys.setdefaultencoding('utf8')

def cleanline(line):
    return line.strip()

def filter_and_display():
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
    

    if not options.hosts:
       sys.exit(1) 
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    filter_and_display()
