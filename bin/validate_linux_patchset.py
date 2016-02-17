#!/usr/bin/python
"""Script to validate solaris patch sets completed successfully. Looks at kernel version and logs"""

from datetime import datetime, date, timedelta
import sys
import re
import subprocess
import logging
from optparse import OptionParser
import glob
import common
import json
import os.path

def check_release(input):
    ver = 'unknown'
    m = re.search(r' release (\d{1,2}\.\d{1,2})',input)
    if m:
        ver = m.group(1)
    return ver

def check_kernel(input):
    details = input.split()
    kernel = details[2]
    return kernel

def get_os_type():
    os_types = {'OEL': '/etc/oracle-release', 'RHEL': '/etc/redhat-release', 'CENTOS': '/etc/centos-release'}
    os_type = ''
    if os.path.isfile(os_types['OEL']):
        os_type = 'OEL'
    elif os.path.isfile(os_types['CENTOS']):
        os_type = 'CENTOS'
    elif os.path.isfile(os_types['RHEL']):
        os_type = 'RHEL'
    else:
        os_type = 'UNKNOW'
    return os_type

def get_os_ver(os_type):
    os_types = {'OEL': '/etc/oracle-release', 'RHEL': '/etc/redhat-release', 'CENTOS': '/etc/centos-release'}
    cmd_lst = ['cat', os_types[os_type]]
    release = run_cmd(cmd_lst)
    ver = check_release(release)
    return ver

def getGlibcVer(glibc_ver):
    result = False
    cmd_lst = ['rpm', '-q', 'glibc']
    installed_glibc_ver = run_cmd(cmd_lst).rstrip()
    for glibc in installed_glibc_ver.split('\n'):
        if re.search(r'x86_64', glibc):
            result = False if glibc != glibc_ver else True
            logging.debug("Current : %s | Wanted : %s | Check : %s" % (glibc, glibc_ver, result))
    return result

def get_release(os_ver, os_type):
    os_types = {'OEL': '/etc/oracle-release', 'RHEL': '/etc/redhat-release', 'CENTOS': '/etc/centos-release'}
    logging.debug(os_ver)
    cmd_lst = ['cat', os_types[os_type]]
    release = run_cmd(cmd_lst)
    ver = check_release(release)
    result = False if ver != os_ver else True
    logging.debug("Current : %s | Wanted : %s | Check : %s" % (ver, os_ver, result))
    return result

def run_cmd(cmdlist):
    logging.debug(cmdlist)
    run_cmd = subprocess.Popen(cmdlist, stdout=subprocess.PIPE)
    out, err = run_cmd.communicate()
    return out

def get_kernel_ver(kernver):
    logging.debug(kernver)
    cmd_lst = ['uname', '-a']
    uname = run_cmd(cmd_lst)
    ver = check_kernel(uname)
    result = False if ver != kernver else True
    logging.debug("Current : %s | Wanted : %s | Check : %s" % (ver, kernver,result))
    return result

def check_uptime(limit):
    cmd_lst = ['cat', '/proc/uptime']
    proc_uptime = run_cmd(cmd_lst)
    uptime,idle = proc_uptime.split()
    result = True if float(uptime) < float(limit) else False
    logging.debug('%s %s %s' % (uptime, limit, result))
    logging.debug(limit)
    logging.debug(result)
    return result


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

    %prog [-c (current|candidate)] [-f path/to/json/file] [-u] [-v]
    %prog [-k kernel] [-r redhat] [-b seconds] [-u] [-v]

    Validate the host needs patching.
    %prog -c current -f valid_versions.json

    Validate the host has been updated
    %prog -c current -f valid_versions.json -u

    Valdiate the kernel version
    %prog -k <kernel version>

    Validate the redhat release
    %prog -r <redhat release>

    Validate both the kernel and redhat release
    %prog -k kernel -r release

    Valdaite if the system is already updated or not
    %prog -k kernel -r release -u

    Usage before patching to check if you need to apply the update
    %prog -k 2.6.32-504.8.1.el6.x86_64 -r 6.6

    Usage after patching to check if the host has been updated and rebooted within the last 5 mins
    %prog -k 2.6.32-504.8.1.el6.x86_64 -r 6.6 -u
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
    os_type = get_os_type()
    os_ver = get_os_ver(os_type)
    os_major,os_minor = os_ver.split('.')
    glibc_ver = False
    logging.debug('OS: %s, Major: %s, Minor: %s' % (os_type,os_major,os_minor))
    if options.check and options.updated:
        kern_result = get_kernel_ver(version_data[os_type][os_major][options.check]['kernel'])
        print('Checking kernel version:')
        exit_code(kern_result)
        rel_result = get_release(version_data[os_type][os_major][options.check]['os_version'],os_type)
        print('Checking RH release version:')
        exit_code(rel_result)
        if 'glibc' in version_data[os_type][os_major][options.check]:
            print('Checking glibc version:')
            glibc_ver = getGlibcVer(version_data[os_type][os_major][options.check]['glibc'])
            exit_code(glibc_ver)
        print('System running correct patch level')
    elif options.check and not options.updated:
        kern_result = get_kernel_ver(version_data[os_type][os_major][options.check]['kernel'])
        rel_result = get_release(version_data[os_type][os_major][options.check]['os_version'],os_type)
        if 'glibc' in version_data[os_type][os_major][options.check]:
            glibc_ver = getGlibcVer(version_data[os_type][os_major][options.check]['glibc'])
        if kern_result == True and rel_result == True and glibc_ver == True:
            print('System running correct patch level no need to update')
            sys.exit(1)
        else:
            print('System not running correct patch level and needs to be updated')
    elif options.kernver:
        result = get_kernel_ver(options.kernver)
        exit_code(result)
    elif options.releasever:
        result = get_release(options.releasever)
        exit_code(result)
    else:
        print(usage)