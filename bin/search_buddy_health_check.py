#!/usr/bin/env python

from __future__ import print_function
import sys
from argparse import ArgumentParser
import logging, time
import requests
from multiprocessing import Process, Queue
from os import path




def get_status(host,p_queue):
    host_dict ={}
    url = "http://{}:8983/solr/metadata/admin/ping".format(host)
    try:
        res = requests.get(url, timeout=30)
        status = res.json()['status']
    except:
        print("Unable to get the status of the host {}".format(host))
        status = "Dead"

    if status.lower() == "ready":
        status = "Alive"
    else:
        status = "Dead"

    host_dict[host] = status

    p_queue.put(host_dict)


def get_buddies(host_list):
    pod = host_list[0].split('-')[0]
    dc = host_list[0].split('-')[3]
    buddy_dict = {}
    for host in host_list:
        set = ['1', '2', '3']
        host_major = host.split('-')[1][:-1]
        host_major_sub = host.split('-')[1][-1]
        host_minor = host.split('-')[2]
        if pod not in host:
            print("Hosts are from different pod. Exiting..")
            sys.exit(1)
        set.remove(host_major_sub)
        buddy1 = ('-').join([pod,host_major+set[0],host_minor,dc])
        buddy2 = ('-').join([pod,host_major+set[1],host_minor,dc])
        buddy_dict[host] = [buddy1, buddy2]
        if buddy1 in buddy_dict or buddy2 in buddy_dict:
            print("Not allowed to work on the Hosts from same triplet. Exiting..\n")
            print(buddy_dict)
            sys.exit(1)

    return buddy_dict


def buddy_check(buddy_dict):
    all_buddies = []
    for buddies in buddy_dict.values():
        all_buddies.append(buddies[0])
        all_buddies.append(buddies[1])

    process_q = Queue()
    p_list = []

    for host in all_buddies:

        process_inst = Process(target=get_status,args=(host,process_q))
        p_list.append(process_inst)
        process_inst.start()
        time.sleep(1)
    buddy_check_response = {}
    for pick_process in p_list:
        pick_process.join()
        buddy_check_response.update(process_q.get())


    include =[]
    exclude = {}
    for key,buddies in buddy_dict.items():
        exclude[key] = []
        exclude_the_host = False
        buddy1 = buddies[0]
        buddy2 = buddies[1]
        buddy1_status = buddy_check_response[buddy1]
        buddy2_status = buddy_check_response[buddy2]
        print("{} --> [{} : {} , {} : {} ]".format(key,buddy1,buddy1_status,buddy2,buddy2_status))
        if buddy1_status == 'Dead':
            exclude[key].append(buddy1)
            exclude_the_host = True
        if buddy2_status == 'Dead':
            exclude[key].append(buddy2)
            exclude_the_host = True
        if exclude_the_host:
            continue
        else:
            del exclude[key]
            include.append(key)

    user_home = path.expanduser('~')

    with open(user_home + '/' + case_num + '_exclude', 'a+') as ex_file:
        for k, v in exclude.items():
            print("\nExcluding the host {}\n".format(k))
            ex_file.write("\n{} - Buddy not alive : {}\n".format(k,v))

    with open(user_home + '/' + case_num + '_include', 'w') as in_file:
            in_file.write(",".join(include))
    if not include:
        print("No servers left to proceed..Exiting\n")
        sys.exit(1)



def main():
    """
    This is main function which will accept the command line argument and pass to the class methods.
    :return:
    """
    parser = ArgumentParser(description="""To check the health status of search buddy hosts""",
                            usage='%(prog)s -H <comma separated host_list> ',
                            epilog='python search_buddy_check.py -H cs12-search41-1-phx,na54-search23-4-phx')
    parser.add_argument("-H", dest="hosts", required=True, help="The hosts in command line argument")
    parser.add_argument("-C", dest="case", required=True, help="Case number")
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    host_list = args.hosts.split(',')
    global case_num
    case_num = args.case
    buddy_dict = get_buddies(host_list)
    buddy_check(buddy_dict)

if __name__ == "__main__":
    main()
