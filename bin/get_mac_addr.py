#!/usr/bin/python

from os import path
import subprocess
import sys


def get_mac_addresses():

    mac_cmd = "ifconfig eth0 | grep HWaddr | awk '{print $NF}'"
    ib_mac_cmd = "ipmitool lan print | grep 'MAC Address' | awk '{print $NF}'"

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
    get_mac_addresses()


if __name__ == "__main__":
    main()
