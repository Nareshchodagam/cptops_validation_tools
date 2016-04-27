#!/usr/bin/python
"""Script to validate which os is being worked on"""

import sys
import re
import subprocess
import logging
from optparse import OptionParser
import os.path
import platform

ib_file = os.path.expanduser('~/releaserunner/remote_transfer/ib-passwd-rotation.sh')

def getIBCreds(ib_file):
    try:
        if os.path.isfile(ib_file):
            logging.debug('%s found' % ib_file)
            # getting data from the ib file
            data = getIBFile(ib_file)
            # getting the password from the data
            parseIBFile(data)
    except Exception as e:
        print('File %s not found %s' % (ib_file, e))

def parseIBFile(data):
    passwd = ''
    for l in data:
        l = l.rstrip()
        str = "ADMIN_PW='(.*)'"
        m = re.match(str, l)
        if m:    
            passwd = m.group(1)
    
    if passwd != '':
        print(passwd)
    else:
        print('Problem getting the password. Exiting.')
        sys.exit(1)
        
def getIBFile(ib_file):
    with open(ib_file, 'r') as f:
        data = f.readlines()
    return data    
    
        
if __name__ == "__main__":
    usage = """
    Get the ib_creds from a file. Output is the password
    
    todo : %prog [-f pathtocredsfile] [-v]
    todo : %prog -f ~/releaserunner/remote_transfer/ib-passwd-rotation.sh -v
    
    %prog [-v]
    %prog -v
    
    
    """
    parser = OptionParser(usage)
    parser.add_option("-t", dest="ostype", action="store", help="The os type to match")
    parser.add_option("-v", action="store_false", dest="verbose", help="verbosity")
    (options, args) = parser.parse_args()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    getIBCreds(ib_file)

