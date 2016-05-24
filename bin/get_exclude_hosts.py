#!/usr/bin/env python
from optparse import OptionParser
import base64
import logging
import re
import sys
import os


def getData(fname):
    # read the data from a file
    with open(fname, 'r') as input_data:
        d = input_data.readlines()
        return d

def writeData(fname,data):
    # write the data to a file
    with open(fname, 'w') as output_data:
        for h in data:
            w = h + "\n"
            output_data.write(w)

def parseData(data):
    # Search for the hosts with Exit Code: 1 from RR output
    hosts = []
    for l in data:
        m = re.search(r'@(.*): Exit Code: 1', l)
        if m:
            host = m.group(1)
            hosts.append(host)
            logging.debug(host)        
    return hosts



if __name__ == '__main__':
    
    usage = """
    Script for generating exclude list from RR output    
    
    %prog [ -f filename ] [ -o outputfilename ] [ -v ]
    
    The default output filename is exclude_hosts.txt
    """
    parser = OptionParser(usage)
    parser.set_defaults(outputname='exclude_hosts.txt')
    parser.add_option("-f", "--filename", dest="filename", help="Filename with data to parse")
    parser.add_option("-o", "--outputname", dest="outputname", help="Filename to output data")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity") # will set to False later
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    pp = pprint.PrettyPrinter(indent=4)
    app_vers = {}
    output_file = options.outputname
    
    if options.filename:
        logging.debug(options.filename)
        data = getData(options.filename)
        hosts = parseData(data)
        logging.debug(hosts)
        writeData(options.outputname, hosts)
    
    
