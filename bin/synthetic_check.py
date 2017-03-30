#!/usr/bin/python

# W-3773536
# T-1747263

from argparse import ArgumentParser, RawTextHelpFormatter
import multiprocessing as mp
import requests
import sys
import time
import logging


def get_data(vip):
    """
    :param vip: vip of cluster
    :return:
    """
    try:
        #url = 'http://%s/api' % (vip) # Test URL 
        url = 'https://%s/api/monitor/syntransaction' % (vip)
        page = requests.get(url)
        pjson = page.json()
        return pjson
    except:
        pass


def check_app_state(vip, host):
    """
    :param vip: 
    :param host: 
    :return: 
    """
    try:
        vdict = get_data(vip)
        result = False
        if host == 'clusterHealth':
            if vdict['clusterHealth'] == "OK":
                result = True
            elif vdict['clusterHealth'] == "DOWN":
                result = False
        else:
            if vdict['nodesHealth'][host + ".ops.sfdc.net"] == "OK":
                result = True
            elif vdict['nodesHealth'][host + ".ops.sfdc.net"] == "DOWN":
                result = False
        return result
    except:
        print("Synthetic URL is DOWN.")
        pass


def cont_app_check(host, ncount):
    """

    :param host: 
    :param ncount: 
    :return: 
    """
    result = False
    seconds = 10
    count = 0
    print("Pausing checking for %s seconds while %s Synthetic URL is Showing OK." % (delay, host))
    time.sleep(delay)
    while result != True:
        if count == ncount:
            print("Synthetic URL is still Showing DOWN for %s. Exiting, Check Manually." % host)
            return result
            sys.exit(1)
        result = check_app_state(vip, host)
        if result is True:
            break
        print("Retrying Synthetic URL Check %s in %s seconds" % (host, seconds))
        time.sleep(seconds)
        count += 1
    print("Synthetic URL for %s is Showing OK." % host)
    return result


def que_get_app_state(queue, hosts_completed):
    """
    :param vip: 
    :param hosts_completed: 
    :return: 
    """
    while True:
        host, ncount = queue.get()
        result = cont_app_check(host, ncount)
        if result == False:
            queue.task_done()
            hosts_completed[host] = False
            break
        hosts_completed[host] = True
        queue.task_done()
    return


def que_put_app_state(hosts, ncount):
    """

    :param hosts: 
    :param ncount: 
    :return: 
    """
    queue.put(['clusterHealth', ncount])
    for host in hosts:
        q_lst = [host, ncount]
        queue.put(q_lst)


def host_comp(hosts_completed):
    """
    :param hosts_completed: 
    :return: 
    """
    for key in hosts_completed:
        if hosts_completed[key] == False:
            print('Error with one of the hosts')
            print(hosts_completed)
            sys.exit(1)
    print(hosts_completed)


def invoke_mp():
    """

    """
    for i in range(len(hosts) + 1):
        p = mp.Process(target=que_get_app_state, args=(queue, hosts_completed))
        p.daemon = True
        p.start()

    que_put_app_state(hosts, ncount)
    queue.join()


if __name__ == "__main__":
    parser = ArgumentParser(description="""This code is to check the return code from remote API
    python synthetic_check.py -V umps1c4.salesforce.com:443 -H cs12-ffx41-1-phx""",
                            usage='%(prog)s -V <vip> -H <host_list>',
                            formatter_class=RawTextHelpFormatter)
    parser.add_argument("-V", dest="vip", required=True, help="Vip of cluster")
    parser.add_argument("-H", dest="hosts", required=True, help="Hosts list or Comma seprated hosts")
    parser.add_argument("-d", dest="delay", default=2, type=int, help="The pause to delay while host shows OK")
    parser.add_argument("-c", dest="ncount", default=30, type=int, help="The pause to delay host n*10")
    parser.add_argument("-v", dest="verbose", action="store_true", help="verbosity")

    args = parser.parse_args()

if args.verbose:
    logging.basicConfig(level=logging.DEBUG)

if (args.vip or args.hosts) is None:
    print(parser)
    sys.exit()

if args.vip and args.hosts:
    hosts_completed = {}
    queue = mp.JoinableQueue()
    vip = args.vip
    hosts = args.hosts.split(',')
    delay = args.delay
    ncount = args.ncount

    invoke_mp()
    logging.debug(hosts_completed)
    host_comp(hosts_completed)