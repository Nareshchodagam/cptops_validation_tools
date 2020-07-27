#!/usr/bin/env python

"""
wrapper for orb-check
will be copied to ~/remote_transfer directory of the target host in bootstrap step of patching template
accepts two bundles (one each for CE6 and CE7), runs on target host and invokes orb-check.py on target host with appropriate bundle
ex: ./validate_patchset.py --osce6 [current|canary|xxxx.xxxx] --osce7 [current|canary|xxxx.xxxx]
                    OR
    ./validate_patchset.py --bundle [current|canary|xxxx.xxxx]
    xxxx.xxxx - explicit bundle name

TODO: make this script work independent of orb-check.py

"""

import sys
import os
import socket
import subprocess
import re
import argparse

ORB_FILE = "/usr/local/libexec/orb-check.py"


def get_os_version():
    if not os.path.isfile("/etc/centos-release"):
        print("Not a CentOS host. exiting!")
        sys.exit(1)
    cmdlist = ["cat", "/etc/centos-release"]
    run_cmd = subprocess.Popen(cmdlist, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = run_cmd.communicate()
    if not err:
        ver = None
        m = re.search(r' release (\d{1,2}\.\d{1,2})', out)
        if m:
            ver = m.group(1)
        try:
            ver = ver.split(".")[0]
        except Exception:
            ver = ""
        return ver
    else:
        print("Unable to read file /etc/centos-release. exiting!")
        sys.exit(1)


def run_orb_check(bundle):
    cmdlist = [ORB_FILE, "-v", bundle]
    run_cmd = subprocess.Popen(cmdlist, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = run_cmd.communicate()
    if not err:
        out = out.lower()
        if ("does not match" in out or "reboot required" in out or "action required" in out or "unrecognized arguments" in out or "valueerror" in out):
            print(out)
            sys.exit(1)
        else:
            print(out)
            sys.exit(0)
    else:
        print(err)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="orb_check_wrapper")
    parser.add_argument("--osce6", dest="osce6", help="Patch bundle for CE6")
    parser.add_argument("--osce7", dest="osce7", help="Patch bundle for CE7")
    parser.add_argument("--bundle", dest="bundle", default=False, help="Common Patch bundle for CE7/CE6")
    args = parser.parse_args()

    # exit if orb-check.py is not present on the host
    if not os.path.isfile(ORB_FILE):
        print("orb-check.py is not found. exiting!")
        sys.exit(1)

    # get os major version of the host
    os_version = get_os_version()
    if not os_version in ["6", "7"]:
        print("Found an invalid value for OS version: {0}. Exiting!".format(os_version))
        sys.exit(1)

    # execute orb-check.py with appropriate bundle arg
    if args.bundle:
        run_orb_check(args.bundle)
    elif os_version == "6":
        run_orb_check(args.osce6)
    else:
        run_orb_check(args.osce7)


if __name__ == "__main__":
    main()
