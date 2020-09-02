#!/usr/bin/python

from argparse import ArgumentParser
import json
import re
import sys
from os import path

user_home = path.expanduser("~")


def read_hostlist(casenum):
    if not path.exists("%s/%s_include" % (user_home, casenum)):
        print("%s/%s_include not found. Exiting" % (user_home, casenum))
        sys.exit(1)
    file_name = user_home + "/" + casenum + "_include"
    f = open(file_name, "r")
    return str(f.readline().rstrip("\n").rstrip(",")).split(",")


def getData(filename):
    if not path.exists(filename):
        print("%s file not found. Exiting" % (filename))
        sys.exit(1)
    with open(filename, 'r') as input_data:
        d = input_data.readlines()
    return d


def parseData(data, data_type, hostname):
    if data_type == "ib":
        pattern = "%s: IB_MAC_ADDRESS: " % hostname
    elif data_type == "host":
        pattern = "%s: HOST_MAC_ADDRESS: " % hostname
    for line in data:
        if re.search(pattern, line):
            break
    mac = line.split(pattern)[-1].rstrip()
    return mac


def main():
    parser = ArgumentParser()
    parser.add_argument("-c", dest="case_number", required=True)
    parser.add_argument("-f", dest="input_file", required=True)
    parser.add_argument("-o", dest="output_file", required=True)

    args = parser.parse_args()

    raw_log = args.input_file
    output = args.output_file
    casenum = args.case_number

    data = getData(raw_log)
    host_list = read_hostlist(casenum)
    if not host_list:
        print("Host list is empty. Exiting")
        sys.exit(1)

    mac_address_data = {}

    for h in host_list:
        mac_address_data.update({h: {}})
        ib_mac = parseData(data, "ib", h)
        host_mac = parseData(data, "host", h)
        mac_address_data[h].update({"IB_MAC_ADDRESS": ib_mac, "HOST_MAC_ADDRESS": host_mac})

    with open(output, "w") as op:
        json.dump(mac_address_data, op, indent=4)

if __name__ == "__main__":
    main()
