#!/usr/bin/env python

# imports
import urllib
import argparse
from re import search, compile
import sys
import logging
import socket
from idbhost import Idbhost


# Where am I
def where_am_i():
    """
    Figures out location based on hostname

    :param: nothing
    :return: 3 letter site code
    """
    hostname = socket.gethostname()
    logging.debug(hostname)
    if not search(r'(sfdc.net|salesforce.com)', hostname):
        short_site = 'sfm'
    elif search(r'internal.salesforce.com', hostname):
        short_site = 'sfm'
    else:
        inst,hfuc,g,site = hostname.split('-')
        short_site = site.replace(".ops.sfdc.net", "")
    logging.debug(short_site)
    return short_site


# idb class instantiate
def idb_connect(site):
    """
    Intitiate connection to idb based on the site.
    :param site: The site name
    :rtype: Make a connection to idb based on the site.

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


# Function to get the pod_list
def get_site_pod(hostlist):
    """
    This function is to create a dict of pod as keys and value as hostname. It will return the dict and  the datacenter
    name

    :param hostlist: The list of hostnames
    :return pod, dc: Return the dictionary with pod as key and hostnames as values and datacenter name
    :type arg1: A list
    """

    pod = {}
    for host in hostlist:
        if not pod.has_key(host.split('-')[0]):
            pod[host.split('-')[0]] = [host]
        else:
            pod[host.split('-')[0]].append(host)
    dc = hostlist[0].split('-')[3]
    return pod, dc


# Function to  query the web
def query_to_web(pod):
    """
    This function is to connect to remote url based on the POD name \
    e.g http://na44.salesforce.com/sfdc/monitor/qpidBrokerStatus.jsp

    :param pod: Take the POD name as parameter and query to remote url
    :type arg1: string
    :return: nothing
    :
    """
    url = 'http://%s.salesforce.com/sfdc/monitor/qpidBrokerStatus.jsp' % pod
    logging.debug("Connecting to url %s " % url)
    try:
        file_handle = urllib.urlopen(url).read()
        result = parse_web(file_handle, pod)
        try:
            for key, val in result.iteritems():
                if val.upper() != 'ACTIVE':
                    prob_host[key] = val
        except:
            print('ERROR: Fetched empty data from %s' % url)
            err_inst[pod] = "ERROR"
    except:
        print("ERROR: Can't connect to remote url for inst %s " % pod)
        err_inst[pod] = "ERROR"


# Function for web-scrapping
def parse_web(data, pod):
    """
    This function is used in the query_to_web function and will parse the data.

    :param data: data captured from remote url
    :param pod:  The pod name for parsing
    :type arg1: data from web
    :type arg2: string
    :return: return the dict with match pattern else return none
    """
    com_patt = compile('(%s.*?)\|\d+\|(\w+)' % (pod))
    ser_patt = com_patt.findall(data)
    logging.debug(ser_patt)
    status = {}
    if ser_patt:
        for each in ser_patt:
            status[each[0]] = each[1]
        return status
    else:
        return None


# Function to control the exit_status
def exit_status():
    """
    Function to control the exit status. This is useful while you are running code as commands in katzmeow and
    the command failed.
    As default, the KZ exit with status 1, but this fucntion will give you control to handle the exit status even
    the command as failed or passed.
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

    site = where_am_i()
    idb = idb_connect(site)
    pod_list, dc = get_site_pod(hostlist)
    pod_status = idb.checkprod(pod_list.keys(), dc)
    pod_status = {k.lower(): v for k, v in pod_status.items()}
    for pod, hosts in pod_list.iteritems():
        try:
            if pod_status[pod] != True:
                print("This is DR for site %s, so skipping the buddy pair check!!! " % pod)
            elif pod_status[pod] == True:
                query_to_web(pod)
        except KeyError as e:
            print("ERROR- Invalid key, Instance name is not valid %s" % e)
            prob_host[pod] = "ERROR"

    if prob_host or err_inst:
        print("-" * 50)
        print('\t \t ERROR')
        print("-" * 50)
        print(prob_host)
        print(err_inst)
        exit_status()
