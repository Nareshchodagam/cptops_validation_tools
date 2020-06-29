#!/opt/sfdc/python27/bin/python

import logging
import sys
from argparse import ArgumentParser, RawTextHelpFormatter
import requests
logging.getLogger().setLevel(logging.INFO)


if __name__ == "__main__":
    parser = ArgumentParser(description=""" This script checks if a host is part of the dark cluster.""",
    usage='%(prog)s -H <comma_separated_host_list> -c cluster_name ', formatter_class=RawTextHelpFormatter)
    parser.add_argument("-H", dest="hosts", help="comma_separated_host_list")
    parser.add_argument("-c", dest="cluster", help="Cluster name.")
    args = parser.parse_args()

    if not args.cluster or not args.hosts:
        logging.error("Please pass hostlist and cluster name to the script")
        sys.exit(1)
    host_list = args.hosts.split(',')
    url = "https://"+args.cluster.lower()+".salesforce.com/sfdc/admin/solr/StagingEnvironment?rt=dark_cluster_hosts"
    dark_hosts = []

    try:
        logging.info("Connecting to {0}".format(url))
        ret = requests.get(url)
        if ret.status_code != 200:
            print("Could not connect to the remote url {0}\nExiting!!! ".format(url))
            sys.exit(1)
        else:
            try :
                data = ret.json()["DARK_CLUSTER_HOSTS"]
            except:
                print("Couldn't get the dark cluster hosts. Exiting!!!")
                sys.exit(1)
    except requests.ConnectionError as e:
        print("Couldn't connect to on remote url {0}\nExiting!!!".format(url))
        sys.exit(1)

    for host in data:
        dark_hosts.append(host.split(".")[0])

    all_dark = True
    for host in host_list:
        if host not in dark_hosts:
            logging.error("The host {0} is not part of the dark cluster {1}".format(host,args.cluster))
            all_dark = False
    if not all_dark:
        logging.info("Exiting!!!")
        sys.exit(1)
    else:
        logging.info("All the given hosts are part of dark cluster {}".format(args.cluster))

