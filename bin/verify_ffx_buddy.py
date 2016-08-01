#!/usr/bin/env python
''' 
    Title - 
    Author - CPT - cptops@salesforce.com
    Status - Active
    Created -  07/25/2016
'''

import logging
import socket
import sys
import urllib2
from argparse import ArgumentParser, RawTextHelpFormatter
from re import search
from socket import gethostname

from idbhost import Idbhost


# Where am I
def where_am_i():
    """
    This function will extract the DC/site name form where you are executing your code.

    :param: This function doesn't require any parameter to pass.
    :return: This function will return the side/DC name e.g sfm/chi/was/tyo etc....
    """
    hostname = gethostname()
    logging.debug(hostname)
    if not search(r'(sfdc.net|salesforce.com)', hostname):
        short_site = 'sfm'
    elif search(r'internal.salesforce.com', hostname):
        short_site = 'sfm'
    else:
        inst, hfuc, g, site = hostname.split('-')
        short_site = site.replace(".ops.sfdc.net", "")
    logging.debug(short_site)
    return short_site


# idb class instantiate
def idb_connect(site):
    """
    Initiate connection to idb based on the site/DC name.

    :param site: The site name
    :type site: string
    :return: This function will return a class instance.
    :rtype:  Instance

    """
    try:
        logging.debug('Connecting to CIDB')
        if site == "sfm":
            idb = Idbhost()
        else:
            idb = Idbhost(site)
        return idb
    except:
        print("Unable to connect to idb")
        exit()


def dict_lookup(word, lookup_in):

    """
    Function to lookup a string in the supplied dictionary values

    :param word: String to look up
    :param lookup_in: The dictionary
    :return: True
    :rtype: bool

    """
    for v in lookup_in.values():
        if word in v:
            return True


# Function to control the exit status
def exit_status():
    """
    This function is used to control the exit status of the failed command. This is helpful during the case execution in KZ.

    """
    while True:
        u_input = raw_input("Do you want to exit with exit code '1' (y|n) ")
        if u_input == "y":
            sys.exit(1)
        elif u_input == "n":
            sys.exit(0)
        else:
            print("Please enter valid choice (y|n) ")
            continue


def buddy_check(host):
    """

    :param host: hostname to query for buddy check
    :return: the url data
    :rtype: False OR string
    """
    cluster = host.split("-")[0]
    url = "http://%s.salesforce.com/stats/ffxinstancespaceinfo.jsp" % cluster
    logging.debug("Checking buddy pair of " + host + ".ops.sfdc.net at " + url)
    try:
        url_handle = urllib2.urlopen(url, timeout=10).readlines()
        page = url_handle
        return page
    except urllib2.URLError as e:
        print("ERROR: %s " % e)
        err_dict[host] = "ERROR {0}" .format(e)
        return False


def parse_web(host):
    """
    This function is to parse the HTML page
    :param host: Hostname to parse the page
    :return: Hostname OR False
    """
    page = buddy_check(host)
    if page:
        line_number = 0
        for line in page:
                if host in line:
                        if 'Servers' in line:
                                return (page[line_number+1].split('http')[1].split('8085')[0].lstrip("://").rstrip(":"))
                        else:
                                return (page[line_number-1].split('http')[1].split('8085')[0].lstrip("://").rstrip(":"))
                line_number += 1
    else:
        return False


def check_buddy_host(host):
    """
    This function is used to check the status of app on buddy host.
    :param host: hostname to check the buddy
    :return: nothing
    """
    status = False
    buddy = parse_web(host)
    if buddy:
        dc = buddy.split("-")[3]
        hostname = socket.gethostname()
        if "release" not in hostname:
                print("You are currently running this programme on %s. Please log in to any release host in datacenter  %s\n" % (hostname,
                                                                                                                                dc.upper()))
        else:
            try:
                logging.debug("Found valid release host %s, Checking Ping.jsp for host %s\n" % (hostname, buddy))
                url = "http://%s:8085/ping.jsp" % buddy
                request = urllib2.Request(url)
                handle = urllib2.urlopen(request, timeout=5)
                status = handle.read()
            except:
                err_dict[buddy] = "ERROR"

            if not status:
                err_dict[host] = "ERROR - FFX app on buddy host {0} is not running".format(buddy)
            elif "ALIVE" in status:
                print("FFX App on buddy host %s is Running \n" % buddy)


if __name__ == "__main__":
    parser = ArgumentParser(description="""This code is to check the status of ffx buddy host
    python check_ffx_buddy.py -H cs12-ffx41-1-phx""", usage='%(prog)s -H <host_list>',
                            formatter_class=RawTextHelpFormatter)
    parser.add_argument("-H", dest="hosts", required=True, help="The hosts in command line argument")
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    hosts = args.hosts
    hosts = hosts.split(',')
    err_dict = {}

    for host in hosts:
        check_buddy_host(host)

    if dict_lookup('ERROR', err_dict):
        print(err_dict)
        exit_status()
