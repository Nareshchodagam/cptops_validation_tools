#!/usr/bin/env python

"""
    title - To check if the port has opened on the host
    Author - CPT - cptops@salesfore.com
    Status - Active
    Created - 04-22-2016

"""


# imports
import socket
import argparse
import logging
from sys import exit


def check_port(port):
    result = False
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostname()
    try:
        s.connect((host, port))
        result = True
    except socket.error as e:
        print("Error on connect to host %s: %s" % (host, e))
    s.close()
    return host, result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""This code is to check the port status
        python check_local_port.py -p <ports>""", usage='%(prog)s -p <host_list>',
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("-p", required=True, dest="ports", help="port_lists")
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    (args) = parser.parse_args()

    if args.verbose:
        logging.basicConfig(logging.DEBUG)

    ports = args.ports.split(',')
    port_status = dict()
    for port in ports:
        port = int(port)
        hostname, result = check_port(port)
        port_status[hostname] = result
        if not result:
            print(port_status)
            while True:
                u_input = raw_input("Do you want to exit with exit code '1' (y|n) ")
                if u_input == "y":
                    exit(1)
                elif u_input == "n":
                    exit(0)
                else:
                    print("Please enter valid choice (y|n) ")
                    continue
        else:
            print(port_status)
            exit(0)

