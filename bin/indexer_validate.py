#!/usr/bin/python
# $Id
import re
import sys
import os
import logging
from optparse import OptionParser
import socket
import subprocess

def where_am_i():
    hostname = socket.gethostname()
    logging.debug(hostname)
    inst,hfuc,g,site = hostname.split('-')
    short_site = site.replace(".ops.sfdc.net", "")
    logging.debug(short_site)
    return short_site

def localRemote(host):
    hostname = socket.gethostname()
    hostname = hostname.replace(".ops.sfdc.net", "")
    host = host.replace(".ops.sfdc.net", "")
    if hostname == host:
        return 'local'
    else:
        return 'remote'

def runCmd(cmdlist):
    logging.debug(cmdlist)
    run_cmd = subprocess.Popen(cmdlist, stdout=subprocess.PIPE)
    out, err = run_cmd.communicate()
    return out,run_cmd.returncode

def get_inst_site(host):
    inst,hfuc,g,site = host.split('-')
    short_site = site.replace(".ops.sfdc.net", "")
    return inst,short_site

def get_vfstab_entries():
    filename = '/etc/vfstab'
    vfstab_search = []
    with open(filename) as f:
        for line in f:
            m = re.search('/search/\w{1,2}\d{1,2}', line)
            if m and not re.match("#", line):
                details = line.split()
                vfstab_search.append(details[6])
    return vfstab_search

def parse_vfstab(input):
    logging.debug(input)
    role = False
    for line in input.splitlines():
        m = re.search('/search/\w{1,2}\d{1,2}', line)
        if m and not re.match("#", line):
            details = line.split()
            logging.debug(details[6])
            m = re.search(r'(reader|writer)', details[6])
            if m:
                role = m.group(1)
                logging.debug(role)
    return role

def checkKinit():
    cmdlist = ['klist', '-s']
    output,returncode = runCmd(cmdlist)
    if returncode != 0:
        print('run kinit.')
        sys.exit(1)

def parse_mnttab(inst, input):
    mnt_role = False
    for line in input.splitlines():
        m = re.search('/search/' +inst, line)
        if m and not re.match("#", line):
            details = line.split()
            logging.debug(details[3])
            m = re.search(r'(ro|rw)', details[3])
            if m:
                mnt_role = m.group(1)
                logging.debug(mnt_role)
    return mnt_role

def check_prod(inst, site):
    host = inst+'.salesforce.com'
    primary = socket.getfqdn(host)
    logging.debug("site : %s" % site)
    logging.debug("host : %s" % host)
    logging.debug("primary host : %s" % primary)
    pri_site = re.search(r'-(\w{3}).salesforce.com', primary)
    logging.debug("pri_site : %s" % pri_site.group(1))
    if pri_site.group(1) != site:
        return "DR"
    else:
        return "PROD"

def getInput(host, f):
    local_remote = localRemote(host)
    if local_remote == 'remote':
        checkKinit()
        result=os.popen("ssh  -o StrictHostKeyChecking=no -o \
        ConnectTimeout=5 -n " + host + " \"cat " + f + "\" \
        2>/dev/null").read()
    elif local_remote == 'local':
        result=os.popen("cat " + f).read()

    return result

def checkValid(hosts, site):
    writers = []
    prod = []
    for key in hosts:
        logging.debug(hosts[key])
        if hosts[key][0] == 'writer' and hosts[key][3] == 'DR':
            print('Should only have readers in DR')
            sys.exit(1)
        if hosts[key][0] == 'writer' and hosts[key][3] == 'PROD':
            writers.append(key)
            prod.append(key)
        #if hosts[key][2] == 'PROD':
         #   prod =
    if len(writers) > 1:
        print('Too many writers')
        sys.exit(1)
    elif writers != 1 and prod < 1:
        print('Not enough writers')
        sys.exit(1)
    return writers

def goodToPatch(hosts):
    for key in hosts:
        role, mnt_role, inst, h_site, loc = hosts[key]
        ok = False
        if role == 'reader' and mnt_role == 'ro':
            ok = True
        if ok != True:
            print('Host must be a reader and mounted ro to proceed.')
            print('Investigate if you are on the correct host')
            print(key,hosts[key])
            sys.exit(1)

def mounted(host,details):
    search_mounted = False
    role, mnt_role, inst, h_site, loc = details
    if re.search(r'(rw|ro)', mnt_role):
       search_mounted = True
    print('Mounted /search/%s on %s : %s' % (inst,h,search_mounted))
    return search_mounted

def getData(filename):
    with open(filename, 'r') as f:
        data = f.readlines()
    return data

def checkSAMQFS(data):
    samqfs = []
    for line in data.splitlines():
        if re.search(r'SAM-QFS', line):
            logging.debug(line)
            samqfs.append(line)
    return samqfs


if __name__ == "__main__":

    instructions = '''

    %prog -H hostname [-p] [-m] [-s] [-v]

    '''

    # instantiate an OptionParser object
    parser = OptionParser(instructions)
    parser.add_option("-H", "--hostlist", action="store", dest="hostlist")
    parser.add_option("-p", "--patch", action="store_true", dest="patch")
    parser.add_option("-s", "--samfs", action="store_true", dest="samfs")
    parser.add_option("-m", "--mount", action="store_true", dest="mount")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                        help="verbose")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    if not options.hostlist:
        instructions
        sys.exit()
    #checkKinit()
    site = where_am_i()
    hosts = {}
    samqfsdata = {}
    for host in options.hostlist.split(','):
        logging.debug(host)
        inst,h_site = get_inst_site(host)
        loc = check_prod(inst,site)
        vfstab = getInput(host, '/etc/vfstab')
        mnttab = getInput(host, '/etc/mnttab')
        samqfs_data = getInput(host,'/var/log/syslog')
        samqfsdata[host] = samqfs_data
        mnt_role = parse_mnttab(inst,mnttab)
        logging.debug(mnt_role)
        role = parse_vfstab(vfstab)
        logging.debug(role)
        hosts[host] = [role, mnt_role, inst, h_site, loc]
    writers = checkValid(hosts, site)
    if options.patch:
        goodToPatch(hosts)
    if options.mount:
        for h in hosts:
            search_mounted = mounted(h,hosts[h])
            if search_mounted != True:
                print('/search on %s not mounted correctly' % h)
                sys.exit(1)
    if options.samfs:
        for h in hosts:
            if h in samqfsdata:
                samqfs = checkSAMQFS(samqfsdata[h])
                logging.debug(samqfs)
                if not samqfs == []:
                    print("SAM-QFS messages in syslog on %s. Please investigate" % h)
                    sys.exit(1)

    print(hosts)


