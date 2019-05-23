#!/usr/bin/python

from __future__ import print_function
from datetime import datetime
from datetime import timedelta
import argparse
import json
import re
import shlex
import subprocess
import sys
import urllib2

'''
Client side script to check if a machine is SLA Compliant, Valid or Stale
Default thresholds:
    -SLA compliant is if bundle was replaced by a newer one less than 30 days
    -Valid is if bundle was replaced by a newer one less than 60 days, but more than 30 days ago
To Run:
    ./orb-check.py --SLA 30 --VALID 60
or
    ./orb-check.py

Both of the options above will return the full verbose output. For binary exit codes, there are
two flags that can be invoked.
    ./orb-check.py [-s | -a] [
             or
    ./orb-check.py [-s | -a] --SLA 30 --VALID 60
    -s --state:  Returns if a host is good (0) or bad (1).
                 A host is "good" if it is patched on Current, SLA or Valid,
                 "bad" if it is on a Stale patch level.
    -a --action: Returns if a hosts needs to be patched.
                 Any host on Current (1), Any other patch level (0).
'''

def print_orb_state():
    '''
    Runs the orb-lib.sh script and prints the output as a text string
    Place holder for rewriting orb-lib.sh in Python
    '''
    cmd = shlex.split("/usr/local/libexec/orb-lib.sh")
    #This will print output from the original script
    subprocess.call(cmd)

def run_orb_state():
    '''
    Runs the orb-lib.sh script and returns the output as a string
    '''
    cmd = shlex.split("/usr/local/libexec/orb-lib.sh")
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
    return out

def grab_json_url(inst_server, os_version):
    '''
    Grab ORB-HISTORY.json from the http page and translate into dict object:
    ex: http://ops-inst1-1-prd.eng.sfdc.net/rhel_updates/repos/CE7/HISTORY.json
    '''
    repo_url = "/".join(inst_server.split("/")[:-1])
    json_url = "{0}/ALL/ORB-history.json".format(repo_url)

    try:
        response = urllib2.urlopen(json_url)
        data = json.loads(response.read())
    except Exception as e:
        print("Cannot access: {0}".format(json_url))

    return data[os_version]

def check_status(data, bundle, sla_days, valid_days):
    '''
    Determines if the current path level is SLA compliant or Valid using the
    replaced date of a bundle

    Returns a tuple:(status of bundle, bundle, overdue days)
    '''
    today = datetime.now()

    bundle_replaced = data[bundle]["Replaced"]
    if bundle_replaced == None:
        #status_tup = ("SLA&Current", bundle, None
        status = "SLA&Current"
        overdue = None
        return status, overdue
    else:
        bundle_replaced = bundle_replaced[1]

    bundle_replaced_date = datetime.strptime(bundle_replaced, "%m/%d/%Y")
    delta = today - bundle_replaced_date

    sla_thresh =  bundle_replaced_date + timedelta(days=sla_days)
    stale_thresh = bundle_replaced_date + timedelta(days=valid_days)

    if today <= stale_thresh and today >= sla_thresh:
        status = "VALID"
        overdue = abs(delta.days - int(valid_days))
    elif today <= stale_thresh:
        status = "SLA"
        overdue = abs(delta.days - int(valid_days))
    elif today >= stale_thresh:
        status = "STALE"
        overdue = delta.days - int(valid_days)

    return status, overdue

def print_status(status, bundle, overdue, valid_bundles, patch_date):
    '''
    This method will print out the full verbose output
    '''
    install_date_string = "OSPATCH=[{0}] was installed on {1}".format(bundle, patch_date)
    if status == "SLA&Current":
        print("OSPATCH=[{0}] is SLA compliant, and on the most current patch".format(bundle))
        print(install_date_string)
    elif status == "SLA":
        print("OSPATCH=[{0}] is SLA compliant, becomes STALE in {1} days".format(bundle, overdue))
        print(install_date_string)
        print("VALID BUNDLES={0}".format(valid_bundles))
    elif status == "VALID":
        print("OSPATCH=[{0}] is still VALID for {1} more days".format(bundle, abs(overdue)))
        print(install_date_string)
    elif status == "STALE":
        print("OSPATCH=[{0}] is STALE, overdue by {1} days".format(bundle, overdue))
        print(install_date_string)
        print("VALID BUNDLES={0}".format(valid_bundles))

def valid_bundles(data, bundle, compliance_days):
    '''
    Determines what bundles promoted in the past X days
    returns a list of such "valid" bundles

    All valid bundles include Current + all others that have promoted
    '''
    today = datetime.now()
    valid_bundles = []
    current_bundles = []

    for i in data.keys():
        bundle_current = data[i]["Current"]
        if bundle_current == None:
            continue
        else:
            current_bundles.append(str(i))

    current_bundles.sort()
    current = current_bundles[-1]

    for i in data.keys():
        bundle_replaced = data[i]["Replaced"]

        if bundle_replaced == None:
            continue
        else:
            bundle_replaced = bundle_replaced[1]
            bundle_replaced_date = datetime.strptime(bundle_replaced, "%m/%d/%Y")
            delta = today - bundle_replaced_date

        if delta.days < compliance_days:
            valid_bundles.append(str(i))

    valid_bundles.append(current)
    valid_bundles.sort(reverse=True)

    return valid_bundles

def reboot_check():
    '''
    Compare uname -r output  to /etc/sfdc/release, if they do not match,
    report reboot required
    '''
    get_uname = shlex.split("uname -r")
    uname = subprocess.Popen(get_uname, stdout=subprocess.PIPE).communicate()[0]

    get_etc_sfdc = shlex.split("cat /etc/sfdc-release")
    etc_sfdc = subprocess.Popen(get_etc_sfdc, stdout=subprocess.PIPE).communicate()[0]

    uname_kernel = uname.replace("\n", "")
    sfdc_kernel = re.search("(?<=KERNEL )(.*)",etc_sfdc).group(1)

    if uname_kernel not in sfdc_kernel:
        print("INSTALLED KERNEL: {0}".format(uname_kernel))
        print("PATCH KERNEL: {0}, don't match - reboot required".format(sfdc_kernel))
    else:
        print("INSTALLED KERNEL matches the PATCH KERNEL: {0}".format(uname_kernel))

def patch_install_date():
    '''
    checks the contents of the /etc/sfdc-release and grab the INSTALL entry
    to determine when the patch was installed
    '''
    get_etc_sfdc = shlex.split("cat /etc/sfdc-release")
    etc_sfdc = subprocess.Popen(get_etc_sfdc, stdout=subprocess.PIPE).communicate()[0]

    sfdc_install = re.search("(?<=INSTALL )(.*)",etc_sfdc).group(1)
    install_dt = datetime.strptime(sfdc_install, "%Y%m%d")
    full_install_date = install_dt.strftime("%B %d, %Y")

    return full_install_date

def main():

    parser = argparse.ArgumentParser(description="Client checker")
    parser.add_argument("-S", "--SLA", default=30, action="store_true",
        help="Number of days past that define SLA compliance")
    parser.add_argument("-V", "--VALID", default=60, action="store_true",
        help="Number of days that define the threshold for VALID bundles")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-s", "--status",  action="store_true",
        help="Returns (0) if a host is good (Current, SLA or Valid) or (1) if a host is bad (Stale)")
    #note the const arg is to specify the default value when --action is called - don't confuse with default=X
    group.add_argument("-a", "--action", const="CURRENT", nargs="?",
                       choices=['CURRENT', 'CANDIDATE', 'UNSTABLE'], type=str.upper,
        help="Returns (0) if a host is already on the selected tag (Current is the default), or (1) if not")

    args = parser.parse_args()

    orb_state = run_orb_state()
    inst_server =  re.search("(?<=INST SERVER=)\[(.*?)\]", orb_state).group(1)
    os_version = inst_server.split("/")[-1]
    patch = re.search("(?<=OSPATCH=)\[(.*?)\]", orb_state).group(1)
    json_out = grab_json_url(inst_server, os_version)

    if args.status:
        #check if patch anything other than Stale
        status, overdue_days= check_status(json_out, patch, int(args.SLA), int(args.VALID))
        if status == "STALE":
            print(1)
            print("host is stale")
            sys.exit(1)
        else:
            print(0)
            print("host is not stale")
            sys.exit(0)
    elif args.action == "CURRENT" or args.action == "CANDIDATE" or args.action == "UNSTABLE":
        # check if a host is on or on a newer patch level than the patch level specified
        tag_patch =  re.search("(?<={0}=)\[(.*?)\]".format(args.action), orb_state).group(1)
        tag_patch_dt = datetime.strptime(tag_patch, "%Y.%m%d")
        installed_patch_dt = datetime.strptime(patch, "%Y.%m%d")

        if installed_patch_dt == tag_patch_dt:
            print("No action needed")
            print("Installed patch level: {0} matches {1}: {2}".format(patch, args.action, tag_patch))
            sys.exit(0)
        elif installed_patch_dt > tag_patch_dt:
            print("No action needed")
            print("Installed patch level: {0} is newer than {1}: {2}".format(patch, args.action, tag_patch))
            sys.exit(0)
        else:
            print("Action required")
            print("Installed patch level: {0} is older than {1}: {2}".format(patch, args.action, tag_patch))
            sys.exit(1)
    else:
        if args.SLA and args.VALID:
            # if neither arguments are provided
            print("No arguments provided, using default definition of SLA<30 days and VALID<60 days ")
            print("----------------------------")
        # return normal verbose output
        print_orb_state()
        valid_bundles_list = valid_bundles(json_out, patch, int(args.VALID))
        print("----------------------------")
        status, overdue_days = check_status(json_out, patch, int(args.SLA), int(args.VALID))
        patch_date = patch_install_date()
        print_status(status, patch, overdue_days, valid_bundles_list, patch_date)

        reboot_check()

if __name__ == "__main__":
    main()