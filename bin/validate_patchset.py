#!/usr/bin/python
"""Script to validate solaris patch sets completed successfully. Looks at kernel version and logs"""

from datetime import datetime, date, timedelta
import sys
import re
import subprocess
import logging
from optparse import OptionParser
import glob

def find_lastest_install_data():
    output = False
    today = datetime.now()
    yest = datetime.now() - timedelta(days=1)
    for t in today,yest:
        cur = t.strftime('%Y.%m.%d')
        filename = '/var/sadm/install_data/s10s_rec_patchset_short_' + cur + "*.log"
        logging.debug(filename)
        for f in glob.glob(filename):
            output = f
        if not output == False:
            break
    return output

def parse_install_data(filename):
    str = "Installation of patch set complete. PLEASE REBOOT THE SYSTEM."
    updated = False
    with open(filename, 'r') as f:
        data = f.readlines()
        for l in data:
            if re.match(str, l):
                logging.debug(l)
                updated = True
    return updated

def get_kernel_version(input):
    ver = 'unknown'
    m = re.search(r' Generic_(\d{1,6}-\d{1,2}) ',input)
    if m.group(1):
        ver = m.group(1)
    return ver

def check_system_updated():
    updated = False
    filename = '/var/sadm/system/logs/system_updated'
    today = datetime.now()
    cur = today.strftime('%b %d %Y')
    m,d,y = cur.split()
    # non padded number silliness
    if re.match(r'0',d):
        d = d.replace('0', ' ')
    logging.debug("%s %s %s" % (m,d,y))
    with open(filename, 'r') as f:
        for line in f.readlines():
            regex = m + " " + d + " \d{2}:\d{2}:\d{2} GMT " + y
            if re.search(regex, line) and re.search(r'kernel updated', line):
                logging.debug(line)
                updated = True
    return updated

def run_cmd(cmdlist):
    logging.debug(cmdlist)
    netstat_nfs = subprocess.Popen(cmdlist, stdout=subprocess.PIPE)
    out, err = netstat_nfs.communicate()
    return out

def kernel_ver(kernver):
    logging.debug(kernver)
    uname_lst = ['uname', '-a']
    uname = run_cmd(uname_lst)
    ver = get_kernel_version(uname)
    logging.debug("Current : %s | Wanted : %s" % (ver, kernver))
    if not ver == kernver:
        sys.exit(1)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-k", dest="kernver", action="store", help="The kernel version host should have")
    parser.add_option("-u", dest="updated", action="store_true", help="Check if the host was updated")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    if options.kernver:
        kernel_ver(options.kernver)
    if options.updated:
        updated = check_system_updated()
        if updated == False:
            sys.exit(1)
        install_log = find_lastest_install_data()
        host_updated = parse_install_data(install_log)
        if host_updated == False:
            sys.exit(1)
    print("Host validated as successfully updated")
