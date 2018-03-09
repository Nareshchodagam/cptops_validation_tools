#!/usr/bin/env python

'''
    Title - To check the search buddy host app status
    Author - CPT - cptops@salesforce.com
    Status - Active
    Created -   07-20-2016
'''

# imports
from argparse import ArgumentParser, RawTextHelpFormatter
import json
from idbhost import Idbhost
from socket import gethostname
import logging
from urllib2 import urlopen, URLError
from re import search, compile
import socket
import sys


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

def katz_password():
    site = where_am_i()
    user = pswd = None
    sys.path.append("/opt/cpt/")

    try:
        from km.katzmeow import get_creds_from_km_pipe
        import getpass
        user = getpass.getuser()
        pswd, _, _ = get_creds_from_km_pipe(pipe_file=args.encrypted_creds, decrypt_key_file=args.decrypt_key)
        logging.debug("decoded creds passed by km")
    except ImportError:
        logging.error("could not import the km module, will not decode creds passed in by km")

    return site,user,pswd

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
        user = pswd = None
        if args.encrypted_creds:
            sys.path.append("/opt/cpt/")
            try:
                from km.katzmeow import get_password_from_km_pipe
                import getpass
                user =  getpass.getuser()
                pswd = get_password_from_km_pipe(pipe_file=args.encrypted_creds, decrypt_key_file=args.decrypt_key)
                logging.debug("decoded creds passed by km")
            except ImportError:
                logging.error("could not import the km module, will not decode creds passed in by km")
        idb=Idbhost(site=site, user=user, pswd=pswd)
        return idb
    except:
        print("Unable to connect to idb")
        exit()


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


# Function to  query the web
def query_to_web(pod, host):
    """
    This function is to connect to remote url based on the POD name \
    e.g https://cs12.salesforce.com/sfdc/admin/solr/SolrPeerInfo?serverAddr=cs12-search41-1-phx.ops.sfdc.net:8983

    :param pod: Take the POD name as parameter and query to remote url
    :param hosts: comma separated list of hosts
    :type pod: string
    :type hosts: list
    :return: function will return the data read from the url
    :rtype: str
    """
    #for host in hosts:
    url = 'https://%s.salesforce.com/sfdc/admin/solr/SolrPeerInfo?serverAddr=%s.ops.sfdc.net:8983' % (pod, host)
    logging.debug("Connecting to url %s " % url)
    try:
        file_handle = urlopen(url, timeout=10).read()
        return file_handle
    except URLError as e:
        print("ERROR: %s " % e)


# Function to query for HAPeer
def query_to_hapeer(host):
    """

    :param hostname:
    :return:
    """
    url = 'http://%s.ops.sfdc.net:8983/isAPeerUp.jsp' % (host)
    logging.debug("Connecting to url %s " % url)
    try:
        file_handle = urlopen(url, timeout=10).read()
        return file_handle
    except URLError as e:
        print("ERROR: %s " % e)
        err_dict["Looks like host %s is not reachable, please check " % host] = 'ERROR'


# Function to json parser
def json_parse(pod, host, pod_status):

    """
    Function will call the query_to_web function and extract the buddy pair from json data.

    :param pod: The POD/DC/Site name
    :param hosts: List of hosts
    :param pod_status: This will be a dictionary returned from idb_checkprod function. The dictionary will have key, value. Where
                        key could be the POD and the value could be true/false.
    :type pod: string
    :type hosts: list
    :type pod_status: dict
    :return: Function will return the buddy host.
    :rtype:  list
    """

    try:
        json_data = json.loads(query_to_web(pod, host))
        logging.debug(json_data)
        #if pod_status[pod]:
        buddy = json_data['haPeers']
        return buddy
    except:
        return False


# function to check the idb_status of a host
def idb_status(hostlist):

    """
    Function is used to extract the specific information from idb related for a host or list of hosts.

    :param hostlist: List of hostname
    :type hostlist: list
    :return: Specific extracted data
    :rtype: dict
    """

    idb.gethost(hostlist)
    return idb.mlist


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


# # function to check the port
# def check_port(host, port):
#
#     """
#     Function is used to check the port on the remote host
#
#     :param host: The remote hostname
#     :param port:  The remote port to connect and check
#     :type host: str
#     :type port: int
#     :return: True OR false, based on connection result.
#     :rtype: bool
#
#     """
#     result = False
#     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     try:
#         s.settimeout(5)
#         s.connect((host, port))
#         result = True
#     except socket.error as e:
#         print("Error on connect to host %s: %s" % (host, e))
#     s.close()
#     return result



# main
if __name__ == "__main__":
    parser = ArgumentParser(description="""This code is to check the status of search buddy host
    python check_search_buddy.py -H cs12-search41-1-phx""", usage='%(prog)s -H <host_list>',
                             formatter_class=RawTextHelpFormatter)
    parser.add_argument("-H", dest="hosts", required=True, help="The hosts in command line argument")
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    parser.add_argument("--encrypted_creds", help="Pass creds in via encrpyted named pipe; used by katzmeow")
    parser.add_argument("--decrypt_key", help="Used only with --encrpyted_creds")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    hosts = args.hosts
    hostlist = hosts.split(',')
    err_dict = {}
    site = where_am_i()
    idb = idb_connect(site)
    pod_list, dc = get_site_pod(hostlist)
    pod_status = idb.checkprod(pod_list.keys(), dc)
    logging.debug(pod_list)
    pod_status = {k.lower(): v for k, v in pod_status.items()}
    logging.debug(pod_status)
    for pod, hosts in pod_list.iteritems():
        try:
            for i_host in hosts:
                json_buddy = json_parse(pod, i_host, pod_status)
                if 'false' in query_to_hapeer(i_host):
                    if json_buddy:
                        buddy_hosts = [host.split(':')[0].split('.')[0] for host in json_buddy]
                        logging.debug(buddy_hosts)
                        idb_data = idb_status(buddy_hosts)
                        logging.debug(idb_data)
                        for host in buddy_hosts:
                            if all([idb_data[host]['opsStatus_Cluster'] == 'ACTIVE', idb_data[host]['opsStatus_Host'] == 'ACTIVE']):
                                print("iDB status looks good for host %s, but search buddy is not up on host %s" % (host, host))
                                err_dict[host] = "ERROR - Search buddy is not up"
                            else:
                                err_dict[host] = "ERROR - iDB status not ACTIVE"
                    elif not json_buddy:
                        print("Looks like we received null from the remote url response")
                else:
                    try:
                        print("Search Buddy %s  is up for host %s" % ("".join(json_buddy).split(':')[0], i_host))
                    except:
                        print("Looks like search buddy is up, but can't figure out the buddy host")
        except KeyError as e:
            print('Looks like one of the POD [%s] does not belongs to the the dc [%s]' % (e, dc))
            err_dict[",".join(pod_list.get(pod))] = 'ERROR '

    if dict_lookup('ERROR', err_dict):
        print(err_dict)
        exit_status()

