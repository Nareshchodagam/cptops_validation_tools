#!/usr/bin/python
# $Id
from optparse import OptionParser
import socket
import re
import sys
import logging
import subprocess

def where_am_i():
    hostname = socket.gethostname()
    logging.debug(hostname)
    inst,hfuc,g,site = hostname.split('-')
    short_site = site.replace(".ops.sfdc.net", "")
    logging.debug(short_site)
    return short_site

def get_vfstab_entries():
    filename = '/etc/vfstab'
    vfstab_search = []
    with open(filename) as f:
        for line in f:
            m = re.search('/search/(\w{1,2}\d{1,2})', line)
            if m and not re.match("#", line):
                vfstab_search.append(m.group(1))
    return vfstab_search

def do_mount(inst):
    pass

def get_mnttab():
    filename = '/etc/mnttab'
    mounted_search = []
    with open(filename) as f:
        for line in f:
            if re.search('(/search/\w{1,2}\d{1,2})', line):
                m = re.search('(/search/\w{1,2}\d{1,2})', line)
                if m:
                    mounted_search.append(m.group(1))
    return mounted_search

def check_prod(inst, site):
    host = inst+'.salesforce.com'
    primary = socket.getfqdn(host)
    logging.debug("site : %s" % site)
    logging.debug("host : %s" % host)
    logging.debug("primary host : %s" % primary)
    pri_site = re.search(r'-(\w{3}).salesforce.com', primary)
    if pri_site:
        logging.debug("pri_site : %s" % pri_site.group(1))
        if pri_site.group(1) != site:
            return "DR"
        else:
            return "PROD"
    else:
            return "UNKNOWN"

def check_mounted(vfstab_entries,mnttab_entries,site):
    not_mounted = []
    all_mounted = True
    for inst in vfstab_entries:
        loc = check_prod(inst, site)
        if not loc == 'DR' and not loc == 'UNKNOWN':
            mp = '/search/' + inst
            logging.debug('Primary instance : %s should be mounted' % mp)
            if not mp in mnttab_entries:
                all_mounted = False
                not_mounted.append(mp)
                logging.debug('Primary instance : %s not mounted' % mp)
            else:
                logging.debug('Primary instance : %s is mounted' % mp)
    return all_mounted, not_mounted
    
if __name__ == "__main__":

    # instantiate an OptionParser object
    parser = OptionParser()
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                        help="verbose")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    site = where_am_i()
    vfstab_entries = get_vfstab_entries()
    mnttab_entries = get_mnttab()
    logging.debug(vfstab_entries)
    logging.debug(mnttab_entries)
    all_mounted, not_mounted = check_mounted(vfstab_entries,mnttab_entries,site)
    if all_mounted == True and not not_mounted:
        print('All primary instances mounted as expected')
        sys.exit(0)
    else:
        print('Not all primary instances are mounted as expected')
        print('Exiting with failure')
        print(all_mounted, not_mounted)
        sys.exit(1)
