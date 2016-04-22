#!/usr/bin/env python

# imports
import urllib
import argparse
from re import search, compile
import sys
import pprint
import logging


def query_to_web(host):
    inst = host.split('-')[0]
    url = 'http://%s.salesforce.com/sfdc/monitor/qpidBrokerStatus.jsp' % inst
    logging.debug("Connecting to url %s " % url)
    try:
        file_handle = urllib.urlopen(url).read()
        result = parse_web(file_handle, inst)
        try:
            for key, val in result.iteritems():
                if val.upper() != 'ACTIVE':
                    prob_host[key] = val
        except:
            print('ERROR: Fetched empty data from %s' % url)
            err_inst[inst] = "ERROR"
    except:
        print("ERROR: Can't connect to remote url for inst %s " % inst)
        err_inst[inst] = "ERROR"
        return False

def parse_web(data, inst):
    com_patt = compile('(%s.*?)\|\d+\|(\w+)' % (inst))
    ser_patt = com_patt.findall(data)
    logging.debug(ser_patt)
    status = {}
    if ser_patt:
        for each in ser_patt:
            status[each[0]] = each[1]
        return status
    else:
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""This code is to check the qpidBrokerStatus on MQ hosts
    python check_mq_buddy.py -H cs1-mq1-1-was""", usage='%(prog)s -H <host_list>',
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("-H", required=True, dest="hosts", help="Host_list")
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    (args) = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    hosts = args.hosts
    hostlist = hosts.split(',')
    err_inst = {}
    prob_host = {}
    for host in hostlist:
        query_to_web(host)


    if prob_host or err_inst:
        print( "-" * 70 )
        print('-------ERROR: Problem with qpidBrokerStatus OR cannot connect to remote url -------')
        print("-" * 70)
        print(prob_host)
        print(err_inst)
        while True:
            u_input = raw_input("Do you want to exit with exit code '1' (y|n) ")
            if u_input == "y":
                sys.exit(1)
            elif u_input == "n":
                sys.exit(0)
            else:
                print("Please enter valid choice (y|n) ")
                continue


