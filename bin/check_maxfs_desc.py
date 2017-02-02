#!/usr/bin/python
"""Code that will use squid client to check max file descriptor setting"""

import os
import re
import sys
import socket
import subprocess
import logging
from optparse import OptionParser
import subprocess

def squid_max_file_desc(paths):
    logging.debug(paths)
    for i in paths:
        logging.debug(i)
        filep = '/home/' + i + '/current/sitesproxy/salesforce/conf/squid.nfi'

def checkId():
    if os.geteuid() != 0:
        print("You need to have root privileges to run this script.")
        sys.exit(1)

def limits_max_file_desc():
    filename = '/etc/security/limits.conf'
    with open(filename, 'r') as f:
        for i in f.read().splitlines():
            if not re.match(r'#', i):
                if re.search(r'\*\s*soft\s*hard\s*65', i):
                    print(i)

def check_max_file_desc(paths):
    ports = { 'proxy1': '8084', 'proxy2': '8085' }
    output = {}
    logging.debug(paths)
    logging.debug(ports)
    for i in ports:
        logging.debug(i)
        try:
            s = subprocess.Popen([paths[i], '-p', ports[i], 'mgr:info'], stdout=subprocess.PIPE)
            out, err = s.communicate()
            for line in out.splitlines():
                if re.search(r'Maximum number of file descriptors', line):
                    str,max_file_desc = line.split(':')
                    output[i] = max_file_desc.strip()
        except Exception, e:
            print('Issue with maximum number of file descriptors: ', e)
            sys.exit(1)
    return output

def checkMaxFileDescPP(paths):
    ports = { 'squid': '8080'}
    output = {}
    logging.debug(paths)
    logging.debug(ports)
    for i in ports:
        logging.debug(i)
        try:
            s = subprocess.Popen([paths['squid'], '-p', ports[i], 'mgr:info'], stdout=subprocess.PIPE)
            out, err = s.communicate()
            for line in out.splitlines():
                if re.search(r'Maximum number of file descriptors', line):
                    str,max_file_desc = line.split(':')
                    output[i] = max_file_desc.strip()
        except Exception, e:
            print('Issue with maximum number of file descriptors: ', e)
            sys.exit(1)
    return output

def get_squid_user_squid_cliend_path(user):
    path = '/home/' + user + '/current/sitesproxy/tools/Linux/squid'
    try:
        s = subprocess.Popen(['find', path, '-name', 'squidclient'], stdout=subprocess.PIPE)
        out, err = s.communicate()
        logging.debug(out)
        return out
    except Exception, e:
        print('Unable to find squidclient file: ', e)

def getSquidClientPath(inst):
    paths = {'squid' : '/usr/bin/squidclient'}
    if re.match(r'public', inst):
        if not os.path.isfile(paths['squid']):
            print('squidclient not found in %s' % paths)
            sys.exit(1)
    else:
        #if not os.path.isfile(path['squid']):
        paths = {}
        lst = ['proxy1', 'proxy2']
        for i in lst:
            spath = get_squid_user_squid_cliend_path(i)
            if not spath == None:
                paths[i] = spath.rstrip()
            #if os.path.isfile():
    logging.debug(paths)
    return paths

def validValues(data):
    for k in data:
        logging.debug(data[k])
        if int(data[k]) < 64000:
            print('%s is less then 64k for user %s' %(data[k], k))
            print('Please restart Squid using sudo /etc/init.d/squid restart')
            sys.exit(1)
            
def get_inst(hostname):
    #m = re.search(r'(.*).ops.sfdc.net', hostname)
    m = re.search(r'(.*).[a-z]{3}.sfdc.net', hostname)
    if m:
        short_host = m.group(1)
        lst = short_host.split("-")
    return lst


def get_hostname():
    hostname = socket.gethostname()
    return hostname

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    checkId()
    hostname = get_hostname()
    short_host = hostname.replace(r'.[a-z]{3}.sfdc.net', '')
    inst,hfunc,node,site = get_inst(hostname)
    logging.debug(hostname)
    logging.debug("%s,%s,%s,%s" % (inst,hfunc,node,site))
    paths = getSquidClientPath(inst)
    logging.debug(paths)
    logging.debug(inst)
    if re.search(r'public', inst):
        live_max_file_desc_values = checkMaxFileDescPP(paths)
    else:
        live_max_file_desc_values = check_max_file_desc(paths)
    logging.debug(live_max_file_desc_values)
    validValues(live_max_file_desc_values)
    for k in live_max_file_desc_values:
        print('Max file descriptors %s for user %s on %s' % (live_max_file_desc_values[k], k, short_host))
    #squid_max_file_desc(paths)
    #limits_max_file_desc()
