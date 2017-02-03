#!/usr/bin/env python

from idbhost import Idbhost
import logging
import sys
import urllib2
from socket import gethostname
from argparse import ArgumentParser, RawTextHelpFormatter
import re
import json

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

def chks_importer():
    '''
    Function imports checks.json file.
    '''
    #presets = "/opt/cpt/bin"
    presets = "checks.json"
    with open(presets, 'r') as pre:
        sets = json.load(pre)
    return sets

def where_am_i():
    """
    This function will extract the DC/site name form where you are executing your code.

    :param: This function doesn't require any parameter to pass.
    :return: This function will return the side/DC name e.g sfm/chi/was/tyo etc....
    """
    hostname = gethostname()
    logging.debug(hostname)
    if not re.search(r'(sfdc.net|salesforce.com)', hostname):
        short_site = 'sfm'
    elif re.search(r'internal.salesforce.com', hostname):
        short_site = 'sfm'
    else:
        inst, hfuc, g, site = hostname.split('-')
        short_site = site.replace(".ops.sfdc.net", "")
    logging.debug(short_site)
    return short_site

def find_role(hosts):
    """
    Determine the role of the server based on hostname. 
    Based on the role it will perform the necessary check. 
    """
    rs = re.compile(r'(\w*)(?<!\d)')
    supported_roles = ['mq', 'search', 'ffx', 'nodeapp']
    host_val = host.split('-')[1]
    host_role = rs.search(host_val)
    role = host_role.group()
    if role in supported_roles:
        return role
    else:
        logging.error("Check for %s not supported.", host_val)
        sys.exit(1)
    
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

# Function to get the pod_list
def get_site_pod(hostlist):
    """
    This function is to create a dict of pod as keys and value as hostname. It will return the dict and  the datacenter
    name

    :param hostlist: The list of hostnames
    :return pod, dc: Return the dictionary with pod as key and hostnames as values and datacenter name
    :type arg1: list
    :rtype: list, string
    """

    pod = {}
    for host in hostlist:
        if not pod.has_key(host.split('-')[0]):
            pod[host.split('-')[0]] = [host]
        else:
            pod[host.split('-')[0]].append(host)
    dc = hostlist[0].split('-')[3]
    return pod, dc

def idb_status_check(hosts): #ERRORS OUT IN REGULAR PROGRAM#####
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

def application_ping_check(cust_msg, host, role):
    """
    This function is used to check the status of app on buddy host and Status of Host and Cluster from IDB.
    :param host: hostname to check the buddy and -I (optional) to force IDB check
    :return: ALIVE or DEAD
    """
    #buddy = buddy_find(host)
    status = ''
    logging.debug("Checking Ping.jsp for host %s\n" % (host))
    url = "http://%s:%d/ping.jsp" % (host,sets[role]['ping_port'])
    logging.debug(url)
    try:
        request = urllib2.Request(url)
        handle = urllib2.urlopen(request)
        status = handle.read()
        logging.debug(status)
    except:
        err_dict[host] = "ERROR"
        logging.error("%s not found.", host)
    
    if "ALIVE" not in status:
        err_dict[host] = "ERROR : %s is not running" % (cust_msg)
    elif "ALIVE" in status:
        print("%s is" + bcolors.OKGREEN + " Running " + bcolors.ENDC + "\n") % (cust_msg)

def buddy_find(host):
    """
    This function is used to check the status of app on buddy host.
    :param host: hostname to check the buddy
    :return: Buddy Host
    """
    hp = re.compile(r'(?=(\d))(\d*)')
    hs = host.split('-')
    site, cluster,hostprefix, hostnum = hs[-1], hs[0], hs[1][-2::1], hs[2]
    num = hp.search(hostprefix)
    #num = int(hostprefix)
    num = int(num.group())
    if (num % 2) == 0:
        buddyprefix = str(num - 1)
    else:
        buddyprefix = str(num + 1)
        
    buddyhost = '%s-%s%s-%s-%s' % (cluster, role, buddyprefix, hostnum, site)
    return buddyhost

def getPriSec(pod_details,insts, dc):
    """
    This function takes a dict containing instances per dc broken down 
    by SP and a list of instances to check  
    
    Returns a dict with the instances allocated to primary or secondary 
    """
    instsPROD = {}
    for inst in insts.split(','):
        inst = inst.upper()
        instsPROD[inst] = None

        for sp, pods in pod_details[dc].items():
            ttl_len = len(pods)
            pri_insts = [pods[index]['Primary'] for index in range(0, ttl_len) if 'Primary' in pods[index]]
            if inst in pri_insts:
                logging.debug('found %s in Primary' % inst)
                instsPROD[inst] = 'primary'

            sec_insts = [pods[index]['Secondary'] for index in range(0, ttl_len) if 'Secondary' in pods[index]]
            if inst in sec_insts:
                logging.debug('found %s in Secondary' % inst)
                instsPROD[inst] = 'secondary'
        return instsPROD
    
def query_to_web(url):
    """
    This function is to connect to remote url based on the POD name \
    e.g http://na44.salesforce.com/sfdc/monitor/qpidBrokerStatus.jsp

    :param pod: Take the POD name as parameter and query to remote url
    :type arg1: string
    :return: nothing
    :
    """
    logging.debug("Connecting to url %s " % url)
    try:
        file_handle = urllib2.urlopen(url, timeout=10).read()
        logging.debug(file_handle)
    except URLError as e:
        print("ERROR: %s " % e)
    
    if role == "nodeapp":
        file_handle = json.loads(file_handle)
        return file_handle
    else:
        return file_handle

    
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
    com_patt = re.compile('(%s.*?)\|\d+\|(\w+)' % (pod))
    ser_patt = com_patt.findall(data)
    status = {}
    if ser_patt:
        for each in ser_patt:
            status[each[0]] = each[1]
        return status
    else:
        return None

def nodeapp_check(host, role):
    cust_msg = "Nodeapp ping.jsp check for %s" % (host)
    cust_url = sets[role]['url']
    cust_url = cust_url % (host)
    logging.debug(cust_url)
    
    result = query_to_web(cust_url)
    if result['status'] != "UP" or result['diskSpace']['status'] != "UP":
        err_dict[host] = "ERROR : Application is not running on %s" % (host) 
    elif result['status'] == "UP" and result['diskSpace']['status'] == "UP":
        print("Application on %s is" + bcolors.OKGREEN + " Running " + bcolors.ENDC + "\n") % (host)
    
    url = application_ping_check(cust_msg, host, role)
    
def mq_check(buddy, role):
    pod = host.split('-')[0]
    cust_url = sets[role]['url'] % (pod)
    logging.debug(cust_url)
    
    data = query_to_web(cust_url)
    result = parse_web(data, pod)
    logging.debug(result)
    
    if result[host +".ops.sfdc.net"] == "ACTIVE":
        print("Buddy pair %s(current) <--> %s(buddy) is" + bcolors.OKGREEN + " ACTIVE " + bcolors.ENDC + "\n") % (host, buddy)
    elif result[host +".ops.sfdc.net"] != "ACTIVE":
        err_dict[host] = "ERROR : Buddy pair %s(current) <--> %s(buddy) is not ACTIVE." % (host, buddy)

if __name__ == "__main__":
    parser = ArgumentParser(description="""    Program designed to check the buddy status of a host.
    Currently works for roles MQ, Search, FFX, Nodeapp.""",
    usage='%(prog)s -H <host_list>', formatter_class=RawTextHelpFormatter)
    parser.add_argument("-H", dest="hosts", required=True, help="The hosts in command line argument")
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    site = where_am_i()
    hosts = args.hosts
    err_dict = {}
    hosts_lst = hosts.split(',')
    
    for host in hosts_lst:       
        role = find_role(host)
        logging.debug(role)
        logging.debug(host)
        sets = chks_importer()
        
        if role == "nodeapp":
            nodeapp_check(host, role)
        elif role == "ffx":
            buddy = buddy_find(host)
            cust_msg = "FFX App on buddy host %s" %(buddy)
            url = application_ping_check(cust_msg, buddy, role)
        elif role == "mq":
            buddy = buddy_find(host)
            mq_check(buddy, role)
