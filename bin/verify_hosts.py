#!/usr/bin/env python
'''
    Title -
    Author - CPT - cptops@salesforce.com
    Status - Active
    Created - 10-03-2016
'''

# modules
from __future__ import print_function
import socket
from argparse import ArgumentParser
import logging
from multiprocessing import Process, Queue
from subprocess import Popen, PIPE
from StringIO import StringIO
import shlex
from os import path


class HostsCheck(object):
    """
    :param: Class definition which accepts bundle name and case_no as command line arguments and pass to class methods.
    """
    def __init__(self, bundle, case_no):
        self.bundle = bundle
        self.case_no = case_no
        self.data = []
        self.user_home = path.expanduser('~')

    def check_ssh(self, host, p_queue):
        """
            This function takes a host and check if host is alive and patched/not-patched
            :param: Accept hostname
            :return: Returns a dict with key as hostname and value host_status(Down, patched, no-patched)
            :rtype: dict
        """
        host_dict = {}
        socket_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if host:
                socket_conn.settimeout(10)
                socket_conn.connect((host, 22))
                cmd = 'ssh -o StrictHostKeyChecking=no  %s "rpm -qa | grep sfdc-release |awk -F- \'{print $3}\'"' % host
                split_cmd = shlex.split(cmd)
                p_object = Popen(split_cmd, stdout=PIPE, stderr=PIPE)
                (out, err) = p_object.communicate()
                if str(self.bundle) == out.strip('\n'):
                    host_dict[host] = "patched"
                else:
                    host_dict[host] = "no_patched"
        except socket.error as error:
            host_dict[host] = "Down"
            print("Error on connect: %s" % error)
            socket_conn.close()
        logging.debug(host_dict)
        p_queue.put(host_dict)

    def write_to_file(self):
        """
        This function is to write files based on host_status.
        :param case_no: This is case number used to generate files prefix with case_no
        :param data: This is dictionary contains host as key and host_status as value
        :return: None
        """
        ex_buffer = StringIO()
        in_buffer = StringIO()
        for host_dict in self.data:
            for k, v in host_dict.items():
                if v == 'no_patched':
                    in_buffer.write("{0}".format(k)+',')
                    logging.debug(in_buffer.getvalue())
                else:
                    ex_buffer.write("{0} -  {1}".format(k, host_dict[k])+'\n')
                    logging.debug(ex_buffer.getvalue())
        in_hosts = in_buffer.buf.rstrip(',')
        with open(self.user_home+'/'+self.case_no+'_exclude', 'a+') as ex_file:
            ex_file.write(ex_buffer.getvalue())
        with open(self.user_home+'/'+self.case_no+'_include', 'w') as in_file:
            in_file.write(in_hosts)

    def check_file_empty(self):
        """
        This function is used to check if the case_no_include file is empty.
        If file is empty the program will exit with status 1.
        :return: None
        """
        filename = "{0}/{1}_include".format(self.user_home, self.case_no)
        if path.getsize(filename) == 0:
            raise SystemExit("File {0} is empty, so quitting".format(filename))

    def process(self, hosts):
        """
        This function will accept hostlist as input and call check_ssh function and store value in
        shared memory(Queue).
        :param hosts: A list of hosts
        :return: None
        """
        process_q = Queue()
        p_list = []
        for host in hosts:
            process_inst = Process(target=self.check_ssh, args=(host, process_q))
            p_list.append(process_inst)
            process_inst.start()
        for pick_process in p_list:
            pick_process.join()
            self.data.append(process_q.get())


def main():
    """
    This is main function which will accept the command line argument and pass to the class methods.
    :return:
    """
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
    case_no = args.case
    class_object = HostsCheck(bundle, case_no)
    class_object.process(hosts)
    class_object.write_to_file()
    class_object.check_file_empty()

if __name__ == "__main__":
    main()
