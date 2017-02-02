#!/usr/bin/env python

import logging
import sys
import urllib2
from re import search
from socket import gethostname
from idbhost import Idbhost
from argparse import ArgumentParser, RawTextHelpFormatter


class bcolors:
    HEADER = '\033[34m'
    GREY = '\033[90m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def exit_status():
    """
    This function is used to control the exit status of the failed command. This is helpful during the case execution in KZ.
    """
    while True:
        u_input = raw_input(bcolors.WARNING + "WARNING : " + bcolors.ENDC + " Do you want to exit with exit code '1' (y|n) ")
        if u_input == "y":
            sys.exit(1)
        elif u_input == "n":
            sys.exit(0)
        else:
            print(bcolors.WARNING + "WARNING : " + bcolors.ENDC + " Please enter valid choice (y|n) ")
            continue

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

def format_matrix(header, matrix, top_format, left_format, cell_format, row_delim, col_delim):
    """
    Create a Tabular format for IDB data representation when prog invoked with -I option
    :param: run with -I option
    """
    table = [ header] + [row for name, row in zip(matrix, matrix)]
    table_format = [[bcolors.HEADER + '{:^{}}' + bcolors.ENDC] + len(header) * [top_format]] + len(matrix) * [
        [left_format] + len(header) * [cell_format]]
    
    col_widths = [max(
                      len(format.format(cell, 0))
                      for format, cell in zip(col_format, col))
                  for col_format, col in zip(zip(*table_format), zip(*table))]

    return row_delim.join(
               col_delim.join(
                   format.format(cell, width)
                   for format, cell, width in zip(row_format, row, col_widths))
               for row_format, row in zip(table_format, table))

def idb_status_check(hosts):
    """
    This function is used to check the status of Cluster/Host on IDB.
    :param host: -I to enable
    :return: Tabular Format IDB Status
    """
    idb = idb_connect(site)
    idb.gethost(hosts)
    data = idb.mlist
    row_data = []

    for i in range(len(data.keys())):
        row = data.items()[i][0]
        cluster_s, host_s = data[row]['opsStatus_Cluster'], data[row]['opsStatus_Host']
        buddy = buddy_find(row)
        row_data.append([row, cluster_s, host_s, buddy])

        if 'ACTIVE' not in cluster_s or 'ACTIVE' not in host_s:
            err_dict[row] = 'ERROR - FFX IDB State of Either Host or Cluster is Not ACTIVE for host %s, Check Above Table' % row
        elif 'ACTIVE' in cluster_s or 'ACTIVE' in host_s:
            print('Cluster and Host Status is ' + bcolors.OKGREEN + 'ACTIVE' + bcolors.ENDC + ' in IDB of Host %s.') % row

    headers = ['Hostname','Cluster Status', 'Host Status', 'Buddy Host']
    print (format_matrix(headers, row_data, bcolors.HEADER + '{:^{}}' + bcolors.ENDC, bcolors.GREY + '{:<{}}', '{:>{}}', '\n'  + bcolors.ENDC, ' | '))
    return


def application_ping_check(host):
    """
    This function is used to check the status of app on buddy host and Status of Host and Cluster from IDB.
    :param host: hostname to check the buddy and -I (optional) to force IDB check
    :return: ALIVE or DEAD
    """
    buddy = buddy_find(host)
    status = ''
    try:
        logging.debug("Checking Ping.jsp for host %s\n" % (buddy))
        url = 'http://%s:8085/ping.jsp' % buddy
        request = urllib2.Request(url)
        handle = urllib2.urlopen(request)
        status = handle.read()
    except:
        err_dict[host] = "ERROR"

    if 'ALIVE' not in status:
        err_dict[host] = "ERROR : FFX app on buddy host %s is not running" % buddy

    elif "ALIVE" in status:
        print("FFX App on buddy host %s is" + bcolors.OKGREEN + " Running " + bcolors.ENDC + "\n") % buddy

def buddy_find(host):
    """
    This function is used to check the status of app on buddy host.
    :param host: hostname to check the buddy
    :return: Buddy Host
    """
    hs = host.split('-')
    site, cluster,hostprefix, hostnum = hs[-1], hs[0], hs[1][-1], hs[2]

    if hostprefix == '1':
        buddyprefix = '2'
    elif hostprefix == '2':
        buddyprefix = '1'
    elif hostprefix == '5':
        buddyprefix = '6'
    elif hostprefix == '6':
        buddyprefix = '5'

    buddyhost = '%s-ffx%s-%s-%s' % (cluster, buddyprefix, hostnum, site)
    return buddyhost


if __name__ == "__main__":
    parser = ArgumentParser(description="""This code is to check the status of ffx buddy host
    python check_ffx_buddy_with_idb.py -H cs12-ffx41-1-phx""", usage='%(prog)s -H <host_list>',
                            formatter_class=RawTextHelpFormatter)
    parser.add_argument("-H", dest="hosts", required=True, help="The hosts in command line argument")
    parser.add_argument("-I", dest="idb_status", action='store_true',help="Enable IDB SP/CLUSTER/HOST Status Check")
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    site = where_am_i()
    hosts = args.hosts
    err_dict = {}
    hosts_lst = hosts.split(',')

    if args.idb_status:
        for host in hosts_lst:
            application_ping_check(host)
        idb_status_check(hosts)
    else:
        for host in hosts_lst:
            application_ping_check(host)

    line = 0
    if dict_lookup('ERROR', err_dict):
        for i in err_dict:
            line += 1
            print(bcolors.FAIL +'ERROR#'+ str(line) + bcolors.ENDC +' : %s --> %s' % (i, err_dict[i]))
        exit_status()
