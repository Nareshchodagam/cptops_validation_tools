#!/opt/sfdc/python27/bin/python
'''
This script is used for determining the master node in clusters when this information is not in IDB.
It can be used to recreate the hostlist so thats master nodes are done last. The use case was the
secrets cluster where slave nodes are patched first before master nodes.
'''
import logging
import json
import pprint
import os
import sys
import re
import socket
from argparse import ArgumentParser
import requests

#Set special parameters
requests.packages.urllib3.disable_warnings()
PP = pprint.PrettyPrinter(indent=2)


def get_cluster_info():
    '''
    Determine master server for secrets cluster.
    Sanitize the cluster list to remove unwanted servers.
    :return:
    '''
    slaves = []
    hostlist = args.host.split(",")
    url = "https://{}:8443/vaultczar/api/1.0/doInternalHealthCheck".format(hostlist[0])
    raw_data = requests.get(url, verify=False)
    hostinfo = raw_data.json()
    master = hostinfo['healthchecks'][1]['Master']
    for host in hostinfo['healthchecks'][1]['Slaves']:
        slaves.append(host)

    for host in reversed(slaves):
        if host.split(".")[0] not in hostlist:
            slaves.remove(host)

    return master, slaves

def create_list(master, slaves, master_list, case_list):
    '''
    Function to create the hostlist for the case.
    :param master:
    :param slaves:
    :return:
    '''
    clust_list = {}
    clust_list['Master'] = master
    clust_list['Slaves'] = slaves
    logging.debug(clust_list)
    with open(master_list, 'w') as master, open(case_list, 'w') as case:
        json.dump(clust_list, master)
        case.write(clust_list['Slaves'][0].split(".")[0])

def update_list(case_list, master_list):
    '''
    Function to modify the existing hostlist.
    :return:
    '''
    active_host = get_current(case_list)
    logging.debug("Active Host: {}".format(active_host))
    with open(master_list, 'r') as hst_lst:
        raw_data = json.load(hst_lst)
    try:
        index = raw_data['Slaves'].index(active_host)
        raw_data['Slaves'].pop(index)
    except ValueError:
        print "No More servers to process"
        cleanup(case_list, master_list)
        sys.exit(0)
    fh = open(master_list, 'w')
    json.dump(raw_data, fh)
    fh.close()
    if len(raw_data['Slaves']) != 0:
        fh = open(case_list, 'w')
        fh.write(raw_data['Slaves'][0].split(".")[0])
        fh.close
    else:
        fh = open(case_list, 'w')
        fh.write(raw_data['Master'].split(".")[0])
        fh.close

    return master_list

def get_current(case_list):
    '''
    Function to get the current host.
    :return:
    '''
    domain = re.findall(r'(\..*)', socket.gethostname())
    fh = open(case_list, 'r')
    curr_host = fh.readline().rstrip("\n")
    curr_host = curr_host + str(domain[0])
    fh.close()


    return curr_host

def cleanup(case_list, master_list):
    '''
    Remove all files created by program.
    :return:
    '''
    os.remove(case_list)
    os.remove(master_list)

if __name__ == "__main__":
    parser = ArgumentParser(description="""Create custom hostlist file for clusters.""",
                            usage='%(prog)s -c <case_number>',
                            epilog='check_master.py -c 12344')
    parser.add_argument("-c", "--case", required=True, dest="casenum")
    parser.add_argument("-H", "--host", dest="host")
    parser.add_argument("-u", "--update", action="store_true", dest="update")
    args = parser.parse_args()
    case_list = "{}/{}_include".format(os.path.expanduser('~'), args.casenum)
    master_list = "{}/{}_master".format(os.path.expanduser('~'), args.casenum)
    if args.update:
        filename = update_list(case_list, master_list)
        with open(filename, 'r') as fh:
            json_data = json.load(fh)
            PP.pprint(json_data)
    else:
        master, slaves = get_cluster_info()
        create_list(master, slaves, master_list, case_list)
        with open(master_list, 'r') as fh:
            json_data = json.load(fh)
            PP.pprint(json_data)