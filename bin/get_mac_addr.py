#!/usr/bin/python

import logging
from os import path
import subprocess
import sys


def getVendor():

    logger.debug('Checking dmidecode to identify vendor')

    try:
        cmd = "dmidecode | grep Vendor | awk '{print $2}'"
        result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = result.communicate()
        vendor = out.upper().strip()

        logger.debug("OUT: " + out.rstrip())
        logger.debug("ERR: " + err.rstrip())

    except:
        return False, "error"

    logger.debug("Vendor identified as: " + vendor)
    return True, vendor


def get_mac_addresses(vendor):

    mac_cmd = "ifconfig eth0 | grep HWaddr | awk '{print $NF}'"
    ib_mac_cmd = ""

    if vendor in ["HP", "HPE"]:
        ib_mac_cmd = "ipmitool lan print | grep 'MAC Address:' | awk '{print $NF}'"
    elif vendor == "DELL":
        cmd_util_paths = ['/opt/dell/srvadmin/bin/idracadm7',
                          '/opt/dell/srvadmin/bin/idracadm', '/opt/dell/srvadmin/sbin/racadm']
        util_found = False
        for util in cmd_util_paths:
            if path.exists(util):
                ib_mac_cmd = "%s ifconfig | grep eth0 | awk '{print $NF}'" % util
                util_found = True
            if util_found:
                break
        if not util_found:
            print("error")
            sys.exit(1)
    else:
        print("error")
        sys.exit(1)

    try:
        result = subprocess.Popen(ib_mac_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = result.communicate()
        ib_mac = out.rstrip()

        result = subprocess.Popen(mac_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = result.communicate()
        host_mac = out.rstrip()

        print("IB_MAC_ADDRESS: %s" % ib_mac)
        print("HOST_MAC_ADDRESS: %s" % host_mac)

    except:
        print("error")
        sys.exit(1)


def main():

    status, vendor = getVendor()
    if not status:
        print("error")
        sys.exit(1)
    get_mac_addresses(vendor)


if __name__ == "__main__":
    logger = logging.getLogger()
    logging.basicConfig(level=logging.INFO)
    main()
