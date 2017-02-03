#!/usr/bin/python
"""Script to validate solaris patch sets completed successfully. Looks at kernel version and logs"""

from datetime import datetime, date, timedelta
import sys
import re
import subprocess
import logging
from optparse import OptionParser
import glob

def check_rh_release(input):
    ver = 'unknown'
    m = re.search(r' release (\d{1,2}\.\d{1,2}) ',input)
    if m:
        ver = m.group(1)
    return ver

def check_rh_kernel(input):
    details = input.split()
    kernel = details[2]
    return kernel

def get_rh_release(rhver):
    logging.debug(rhver)
    cmd_lst = ['cat', '/etc/redhat-release']
    release = run_cmd(cmd_lst)
    ver = check_rh_release(release)
    logging.debug("Current : %s | Wanted : %s" % (ver, rhver))
    result = False if ver != rhver else True
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
    ver = check_rh_kernel(uname)
    logging.debug("Current : %s | Wanted : %s" % (ver, kernver))
    result = False if ver != kernver else True
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
        print('Non valid result. exiting')
        sys.exit(1)

if __name__ == "__main__":
    usage = """

    This script will validate if a host is running the correct kernel and redhat release

    %prog [-k kernel] [-r redhat] [-b seconds] [-u]

    Valdiate the kernel version
    %prog -k kernel version

    Validate the redhat release
    %prog -r redhat release

    Validate both the kernel and redhat release
    %prog -k kernel -r release

    Valdaite if the system is already updated or not
    %prog -k kernel -r release -u

    Usage before patching to check if you need to apply the update
    %prog -k 2.6.32-504.8.1.el6.x86_64 -r 6.6

    Usage after patching to check if the host has been updated and rebooted within the last 5 mins
    %prog -k 2.6.32-504.8.1.el6.x86_64 -r 6.6 -b 300 -u
    """
    parser = OptionParser(usage)
    parser.add_option("-k", dest="kernver", action="store", help="The kernel version host should have")
    parser.add_option("-r", dest="releasever", action="store", help="The RH release host should have")
    parser.add_option("-b", dest="boottime", action="store", type = int, default=300, help="The host should have")
    parser.add_option("-u", dest="updated", action="store_true", help="Check if the host was updated")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    if options.kernver and options.releasever and options.updated:
        if options.boottime:
            boottime_result = check_uptime(options.boottime)
            exit_code(boottime_result)
        kern_result = get_kernel_ver(options.kernver)
        print('Checking kernel version:')
        exit_code(kern_result)
        rel_result = get_rh_release(options.releasever)
        print('Checking RH release version:')
        exit_code(rel_result)
        print('System running correct patch level')
    elif options.kernver and options.releasever and not options.updated:
        kern_result = get_kernel_ver(options.kernver)
        rel_result = get_rh_release(options.releasever)
        if kern_result == True and rel_result == True:
            print('System running correct patch level no need to update')
            sys.exit(1)
        else:
            print('System not running correct patch level and needs to be updated')
    elif options.kernver:
        result = get_kernel_ver(options.kernver)
        exit_code(result)
    elif options.releasever:
        result = get_rh_release(options.releasever)
        exit_code(result)
    else:
        print(usage)
