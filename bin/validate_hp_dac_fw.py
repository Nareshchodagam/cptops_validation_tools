#!/usr/bin/python

import sys
import subprocess
import re
from optparse import OptionParser

def check_dac_ver():
    cmd_list = ["sudo", "hpssacli", "ctrl", "all", "show", "config", "detail"]
    p = subprocess.Popen(cmd_list, stdout=subprocess.PIPE)
    (output, err) = p.communicate()
    for line in output.splitlines():
        if re.search('^   Firmware Version: ', line ):
            if line:
                nut = float(line.split(' ')[5])
                return nut

def get_shorthost():
    q = subprocess.Popen("hostname", stdout=subprocess.PIPE)
    (output, err) = q.communicate()
    shorthost = output.split(".")[0]
    return shorthost

if __name__ == "__main__":
    usage = """
    This script will check if the HP array controller firmware needs to be updated

    %prog [-d target_firmware_version]
    """

    parser = OptionParser(usage)
    parser.add_option("-d", dest="target_version", action="store",
        help="The firmware version to which you're upgrading")
    (options, args) = parser.parse_args()
    if options.target_version:
        get_shorthost()
        current_version = check_dac_ver()
        hostname = get_shorthost()
        if current_version < float(options.target_version):
            print "%s: Firmware not up to date" % hostname
            sys.exit(1)
        else:
            print "Host is patched to version %s" % (current_version)
        get_shorthost()
