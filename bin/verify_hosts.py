#!/usr/bin/env python
'''
    Title -
    Author - CPT - cptops@salesforce.com
    Status - Active
    Created -
'''

# modules
import socket
from argparse import ArgumentParser
import logging
from multiprocessing import Pool
from subprocess import Popen, PIPE
from StringIO import StringIO
import shlex


# Function to check ssh connectivity
def check_ssh(host):
    host_dict = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if host:
            s.settimeout(10)
            s.connect((host, 22))
            cmd = 'ssh -o StrictHostKeyChecking=no  %s "rpm -qa | grep sfdc-release |awk -F- \'{print $3}\'"' % host
            split_cmd = shlex.split(cmd)
            p = Popen(split_cmd, stdout=PIPE, stderr=PIPE)
            (out, err) = p.communicate()
            if str(bundle) == out.strip('\n'):
                host_dict[host] = "patched"
            else:
                host_dict[host] = "no_patched"
    except socket.error as e:
        host_dict[host] = "down"
        print("Error on connect: %s" % e)
        s.close()
    logging.debug(host_dict)
    return host_dict


def write_to_file(case_no, data):
    ex_buffer = StringIO()
    in_buffer = StringIO()
    for k, v in data.items():
        if data[k] == 'no_patched':
            in_buffer.write("{0}".format(k)+',')
            logging.debug(in_buffer.getvalue())
        else:
            ex_buffer.write("{0} -  {1}".format(k, data[k])+'\n')
            logging.debug(ex_buffer.getvalue())
    in_hosts = in_buffer.buf.rstrip(',')
    with open(case_no+'_exclude', 'a+') as ex_file:
        ex_file.write(ex_buffer.getvalue())
    with open(case_no + '_include', 'w') as in_file:
        in_file.write(in_hosts)


# main
if __name__ == "__main__":
    parser = ArgumentParser(description="""To check if remote hosts are accessible over SSH and are not patched""",
                                        usage='%(prog)s -H <host_list> --bundle <bundle_name> --case <case_no>',
                                        epilog='python verify_hosts.py -H cs12-search41-1-phx --bundle 2016.09 --case 0012345')
    parser.add_argument("-H", dest="hosts", required=True, help="The hosts in command line argument")
    parser.add_argument("--bundle", dest="bundle", required=True, help="Bundle name")
    parser.add_argument("--case", dest="case", required=True, help="Case number")
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    bundle = args.bundle
    hosts = args.hosts.split(',')
    len_hosts = len(hosts)
    case_no = args.case

    pool = Pool(len_hosts)
    result = pool.map(check_ssh, hosts)
    for item in result:
        write_to_file(case_no, result)

