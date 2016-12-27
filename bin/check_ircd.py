#!/usr/bin/env python

"""
    Title: check to see that [SR] irc daemons are up and linked together
    Author: CPT (cptops@salesforce.com)
    Status: Active
    Created: 12-13-2016
"""

import argparse
import socket

irc_hosts = ['ops-irc1-1-crd.eng.sfdc.net', 'ops-irc2-1-crd.eng.sfdc.net',
             'ops-irc1-1-sfm.ops.sfdc.net', 'ops-irc2-1-sfm.ops.sfdc.net']

def check_irc_links(filename, localhost):
    '''
    check_irc_links function determines our local host and inputs needed data from links.txt
    into a dictionary, which will be used to validate irc daemons are linked.
    '''

    # populate the remote_host localhost dictionary
    irc_dict = {}
    ret_bool = True

    for host in irc_hosts:
        if host == localhost: irc_dict[host] = [" ".join(["services.sfdc.net", localhost]), False]
        else: irc_dict[host] = [" ".join([host, localhost]), False]

    print irc_dict
    # check the links.txt file for presence of all hosts
    with open(filename, 'r') as infile:
        for line in infile:
            for host in irc_dict.keys():
                if line.startswith(irc_dict[host][0]):
                    irc_dict[host][1] = True

    for host, values in irc_dict.items():
        if values[1] == True:
            print "irc host "+host+" found!"
        else:
            print "irc host "+host+" NOT found!"
            ret_bool = False

    return ret_bool


def main():
    '''
    hostname populated with our current host that is being patched.
    '''
    usage = """
    This code will check links.txt for the presence of known IRC hosts. If all hosts are present
    the cluster is considered healthy and the script exits with a 0. Otherwise, it exits with a 1.
    """
    parser = argparse.ArgumentParser(usage)
    parser.add_argument("-H", "--hostname", dest="localhost", default=socket.gethostname(),
                      help="IRC host to check (default: localhost")
    parser.add_argument("-f", "--file", dest="filename", default='/usr/local/ircd/etc/links.txt',
                      help="absolute path to links.txt (default: /usr/local/ircd/etc/links.txt)")
    args = parser.parse_args()

    ret_bool = check_irc_links(args.filename, args.localhost)
    if ret_bool == False: exit(1)
    else: exit(0)


if __name__ == "__main__":
    main()
