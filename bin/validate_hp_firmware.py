#!/usr/bin/python
"""Script to validate solaris patch sets completed successfully. Looks at kernel version and logs"""

from datetime import datetime, date, timedelta
import sys
import re
import subprocess
import logging
from optparse import OptionParser
import glob
import json
import os.path

def check_firmwares(input):
    pass

def run_cmd(cmdlist):
    logging.debug(cmdlist)
    run_cmd = subprocess.Popen(cmdlist, stdout=subprocess.PIPE)
    out, err = run_cmd.communicate()
    return out

def getFirmwareVerions():
    lst = ['raid', 'system', 'ilo']
    results = {}
    cmd_lst = ['/sbin/hpsum', 'list']
    hpsum_output = run_cmd(cmd_lst)
    for l in hpsum_output.splitlines():
        if re.search(r'smartarray', l):
            info,name,ver,installed,type,_ = l.split('|')
            results['smartarray-installed'] = installed.strip(' ')
            results['smartarray-ver'] = ver.strip(' ')
        if re.search(r'system', l):
            info,name,ver,installed,type,_ = l.split('|')
            results['system-installed'] = installed.strip(' ')
            results['system-ver'] = ver.strip(' ')
        if re.search(r'ilo', l):
            info,name,ver,installed,type,_ = l.split('|')
            results['ilo-installed'] = installed.strip(' ')
            results['ilo-ver'] = ver.strip(' ')
    return results

def exit_code(input):
    logging.debug(input)
    if input == False:
        print('Non valid result, run with -v. exiting')
        sys.exit(1)

def get_json(filename):
    with open(filename) as data_file:
        data = json.load(data_file)
    return data

if __name__ == "__main__":
    usage = """

    This script will validate if a host is running the correct kernel and linux release.
    Support for RHEL, OEL and CENTOS currently.


    """
    parser = OptionParser(usage)
    parser.add_option("-k", dest="kernver", action="store", help="The kernel version host should have")
    parser.add_option("-r", dest="releasever", action="store", help="The RH release host should have")
    parser.add_option("-c", dest="check", action="store", help="Check the current or canidate versions")
    parser.add_option("-f", dest="verfile", action="store", help="The host should have")
    parser.add_option("-u", dest="updated", action="store_true", help="Check if the host was updated")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity")
    (options, args) = parser.parse_args()
    
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    if options.verfile:
        versions_file = options.verfile
    else:
        versions_file = 'valid_versions.json'
    
    version_data = get_json(versions_file)
    results = getFirmwareVerions()
    print(results)
