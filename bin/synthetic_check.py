#!/usr/bin/python

# W-3773536
# T-1747263

from argparse import ArgumentParser, RawTextHelpFormatter
import requests
import sys

def get_data(vip):
    """
    :param vip: vip of cluster
    :return:
    """

    url = 'https://%s/api/monitor/syntransaction' % (vip)
    page = requests.get(url)
    pjson = page.json()
    return pjson

def status_check(vip, hosts):
    """
    :param hosts: List of host or Comma seperated hosts.
    :return:
    """
    vdict = get_data(vip)

    if type(hosts) is list:
        print("List of hosts provided")
    elif type(hosts) is str:
        hosts = hosts.split(',')
    else:
        print("Provide valid hostnames")

    for host in hosts:
        if vdict['clusterHealth'] != 'OK':
            print("Cluster is down, Check the output.")
            print(vdict['nodesHealth'])
            sys.exit(1)
        elif vdict['nodesHealth'][host + ".ops.sfdc.net"] != 'OK':
            print("Host %s is down") % (host)
            sys.exit(1)

    print("Cluster and  Hosts heatlh are good.")

if __name__ == "__main__":

    parser = ArgumentParser(description="""This code is to check the return code from remote API
    python synthetic_check.py -V umps1c4.salesforce.com:443 -H cs12-ffx41-1-phx""", usage='%(prog)s -V <vip> -H <host_list>',
                            formatter_class=RawTextHelpFormatter)
    parser.add_argument("-V", dest="vip", required=True, help="Vip of cluster")
    parser.add_argument("-H", dest="hosts", required=True, help="Hosts list or Comma seprated hosts")
    args = parser.parse_args()

    hosts = args.hosts
    vip = args.vip
    if args.vip:
        status_check(vip, hosts)

