#!/usr/bin/env python
'''
    Title -
    Author - CPT - cptops@salesforce.com
    Status - Active
    Created - 10-03-2016
'''

# modules
from __future__ import print_function
import sys, os
if "/opt/sfdc/python27/lib/python2.7/site-packages" in sys.path:
    sys.path.remove("/opt/sfdc/python27/lib/python2.7/site-packages")
try:
    import pexpect
except:
    print("ERROR: pexpect module not found/installed")
    sys.exit(1)
import socket
from argparse import ArgumentParser
import logging
from multiprocessing import Process, Queue
from subprocess import Popen, PIPE
from StringIO import StringIO
import shlex
import json
import unicodedata, re
from os import path

hostname = socket.gethostname()
user_name = os.environ.get('USER')

if re.search(r'(sfdc.net)', hostname):
    sys.path.append("/opt/cpt/km")
    from katzmeow import get_creds_from_km_pipe
    import synnerUtil

class HostsCheck(object):
    """
    :param: Class definition which accepts bundle name and case_no as command line arguments and pass to class methods.
    """

    def __init__(self, bundle, case_no, force=False):
        self.bundle = bundle
        self.case_no = case_no
        self.data = []
        self.user_home = path.expanduser('~')
        self.force = force

    def check_patchset(self, host, passwd, otp, p_queue):
        """
            This function takes a host and check if host is alive and patched/not-patched
            :param: Accept hostname
            :return: Returns a dict with key as hostname and value host_status(Down, patched, no-patched)
            :rtype: dict
        """
        host_dict = {}
        socket_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        orbFile = "/opt/cpt/remote/orb-check.py"
        try:
            fh = open(orbFile, 'r')
        except IOError:
            print("Ensure presence of path: "+orbFile)
        rc = None
        try:
            if host:
                socket_conn.settimeout(10)
                socket_conn.connect((host, 22))
                orbCheckCmd = "python /usr/local/libexec/orb-check.py -a {0}".format(self.bundle)
                orbCmd = "ssh -o StrictHostKeyChecking=no  {0}".format(host)
                child = pexpect.spawn(orbCmd)
                if (child.expect([pexpect.TIMEOUT, "Password:", pexpect.EOF]) == 1) or (child.expect([pexpect.TIMEOUT, "password:", pexpect.EOF]) == 1):
                    child.sendline(passwd)
                if child.expect([pexpect.TIMEOUT, ".*OTP.*", pexpect.EOF]) == 1:
                    child.sendline(otp)
                if (child.expect([pexpect.TIMEOUT, "Password:", pexpect.EOF]) == 1) or (child.expect([pexpect.TIMEOUT, "password:", pexpect.EOF]) == 1) or (child.expect([pexpect.TIMEOUT, ".*OTP.*", pexpect.EOF]) == 1):
                    print("ERROR: Waiting at password/OTP prompt. Either previous password or OTP were not accepted. Please try again.")
                    sys.exit(1)
                child.expect([pexpect.TIMEOUT, ".*]$.*", pexpect.EOF])
                child.sendline(orbCheckCmd)
                child.expect([pexpect.TIMEOUT, ".*]$.*", pexpect.EOF])
                output = str(child.before)
                child.close()
                #print(output)
                if "action required" in output.lower():
                    rc = True
                else:
                    rc = False
                if not rc:
                    host_dict[host] = "patched"
                    print("{0} - already patched".format(host))
                else:
                    host_dict[host] = "no_patched"

        except socket.error as error:
            host_dict[host] = "Down"
            print("{0} - Error on connect: {1}".format(host, error))
            socket_conn.close()
        except Exception as e:
            print(e)
	    exit(1)
        logging.debug(host_dict)
        p_queue.put(host_dict)

    def check_for_centos6(self, host, passwd, otp, p_queue):
        host_dict = {}
        socket_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        try:
            if host:
                socket_conn.settimeout(10)
                socket_conn.connect((host, 22))
                osCheckCmd = "cat /etc/centos-release"
                osCmd = "ssh -o StrictHostKeyChecking=no  {0}".format(host)
                child = pexpect.spawn(osCmd)
                if (child.expect([pexpect.TIMEOUT, "Password:", pexpect.EOF]) == 1) or (child.expect([pexpect.TIMEOUT, "password:", pexpect.EOF]) == 1):
                    child.sendline(passwd)
                if child.expect([pexpect.TIMEOUT, ".*OTP.*", pexpect.EOF]) == 1:
                    child.sendline(otp)
                if (child.expect([pexpect.TIMEOUT, "Password:", pexpect.EOF]) == 1) or (child.expect([pexpect.TIMEOUT, "password:", pexpect.EOF]) == 1) or (child.expect([pexpect.TIMEOUT, ".*OTP.*", pexpect.EOF]) == 1):
                    print("ERROR: Waiting at password/OTP prompt. Either previous password or OTP were not accepted. Please try again.")
                    sys.exit(1)
                child.expect([pexpect.TIMEOUT, ".*]$.*", pexpect.EOF])
                child.sendline(osCheckCmd)
                child.expect([pexpect.TIMEOUT, ".*]$.*", pexpect.EOF])
                output = str(child.before)
                child.close()
                #print(output)
                os = output.find("CentOS release 6")
                if os != -1:
                    host_dict[host] = "Centos6"
                else:
                    host_dict[host] = "NotCentos6"

        except socket.error as error:
            host_dict[host] = "Down"
            print("{0} - Error on connect: {1}".format(host, error))
            socket_conn.close()
        except Exception as e:
            print(e)
	    exit(1)
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
                if v in ('no_patched','Centos6'):
                    in_buffer.write("{0}".format(k) + ',')
                    logging.debug(in_buffer.getvalue())
                else:
                    if self.force and v in ('patched','NotCentos6'):
                        in_buffer.write("{0}".format(k) + ',')
                        logging.debug(in_buffer.getvalue())
                    ex_buffer.write(
                        "{0} -  {1}".format(k, host_dict[k]) + '\n')
                    logging.debug(ex_buffer.getvalue())
        in_hosts = in_buffer.buf.rstrip(',')
        with open(self.user_home + '/' + self.case_no + '_exclude', 'a+') as ex_file:
            ex_file.write(ex_buffer.getvalue())
        with open(self.user_home + '/' + self.case_no + '_include', 'w') as in_file:
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

    def process(self, hosts, kpass):
        """
        This function will accept hostlist as input and call check_patchset function and store value in
        shared memory(Queue).
        :param hosts: A list of hosts
        :return: None
        """
        process_q = Queue()
        p_list = []
        syn = synnerUtil.Synner()
        for host in hosts:
            otp = syn.get_otp()
            process_inst = Process(target=self.check_patchset, args=(host, kpass, otp, process_q))
            p_list.append(process_inst)
            process_inst.start()
        for pick_process in p_list:
            pick_process.join()
            self.data.append(process_q.get())
        
    def os_process(self, hosts, kpass):
        """
        This function will accept hostlist as input and call check_patchset function and store value in
        shared memory(Queue).
        :param hosts: A list of hosts
        :return: None
        """
        process_q = Queue()
        p_list = []
        syn = synnerUtil.Synner()
        for host in hosts:
            otp = syn.get_otp()
            process_inst = Process(target=self.check_for_centos6, args=(host, kpass, otp, process_q))
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
    parser = ArgumentParser(description="""To check if remote hosts are accessible over SSH and are not patched""", usage='%(prog)s -H <host_list> --bundle <bundle_name> --case <case_no>', epilog='python verify_hosts.py -H cs12-search41-1-phx --bundle 2016.09 --case 0012345')
    parser.add_argument("-M", dest="mhosts", help="To get the Centos6 hosts only", action="store_true")
    parser.add_argument("--bundle", dest="bundle", help="Bundle name")
    parser.add_argument("-H", dest="hosts", required=True, help="The hosts in command line argument")
    parser.add_argument("--case", dest="case", required=True, help="Case number")
    parser.add_argument("--force", dest="force", action="store_true", help="Case number")
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    parser.add_argument("--encrypted_creds", dest="encrypted_creds", help="Pass creds in via encrypted named pipe")
    parser.add_argument("--decrypt_key", dest="decrypt_key", help="Used with --encrypted_creds description")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if args.encrypted_creds:
       try:
          kpass, username, _ = get_creds_from_km_pipe(pipe_file=args.encrypted_creds,decrypt_key_file=args.decrypt_key)
          username = username.split('@')[0]
       except ImportError as e:
          print("Import failed from GUS module, %s" % e)
          sys.exit(1)

    if args.bundle:
        bundle = args.bundle
    else:
        bundle = "current"
    hosts = args.hosts.split(',')
    case_no = args.case
    force = args.force
    class_object = HostsCheck(bundle, case_no, force)
    if args.mhosts:
        mhosts=args.hosts.split(',')
        class_object.os_process(mhosts, kpass)
    else:
        hosts=args.hosts.split(',')
        class_object.process(hosts, kpass)
    class_object.write_to_file()
    class_object.check_file_empty()

if __name__ == "__main__":
    main()