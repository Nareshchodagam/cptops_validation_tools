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
import json
import unicodedata
from os import path
import ConfigParser
import sys
sys.path.append("/opt/cpt/")
from km.katzmeow import *
from GUS.base import Auth
from GUS.base import Gus
import os
import urllib
import requests
import re
from socket import gethostname

hostname = gethostname()

configdir = os.environ['HOME']+"/.cptops/config"
config = ConfigParser.ConfigParser()
config.readfp(open(configdir+'/creds.config'))

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
        self.api_version = config.get('GUS', 'api_ver')

    def check_rma(self, host, session):
        """
        This function takes a host and check if RMA/Incidents exists or not.
        :param self
        :param host:
        :param session:
        :return:
        """
        host_dict = {}
        instance_url = session['instance']
        access_token = session['token']
        headers = {
            'Authorization': "Bearer {0}".format(access_token)
        }

        if host:
            query = urllib.urlencode({"q": "SELECT  Case_Record__r.CaseNumber, Case_Record__r.Subject FROM SM_Case_Asset_Connector__c WHERE Tech_Asset__r.Discovered_Host_Name__c like '%"+ host + "%' AND (Case_Record__r.RecordType.Name = 'RMA' OR Case_Record__r.RecordType.Name = 'Incident') AND (NOT Case_Record__r.Status like '%Closed%') AND (NOT Case_Record__r.Status like '%Resolved%') "})
            url = "{0}/services/data/{1}/query/?{2}".format(instance_url, self.api_version, query)
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                response_json = response.json()
                if response_json['records']:
                    for r in response_json['records']:
                        status = "rma" + " " + r['Case_Record__r']['CaseNumber']
                else:
                    status = "not_patched"
        return status

    def check_patchset(self, host, session, p_queue):
        """
            This function takes a host and check if host is alive and patched/not-patched
            :param: Accept hostname
            :return: Returns a dict with key as hostname and value host_status(Down, patched, no-patched)
            :rtype: dict
        """
        host_dict = {}
        socket_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        orbFile = self.user_home+"/remote_transfer/orb-check.py"

        try:
            if host:
                socket_conn.settimeout(10)
                socket_conn.connect((host, 22))
                orbCheckCmd = "python {0} -a {1}".format(orbFile, self.bundle.upper())
                orbCmd = "ssh -o StrictHostKeyChecking=no  {0} {1}".format(host, orbCheckCmd)
                orbCmdOut = Popen(orbCmd, stdout=PIPE, stderr=PIPE, shell=True)

                streamdata, err = orbCmdOut.communicate()
                rc = orbCmdOut.returncode

                if not rc:
                    host_dict[host] = "patched"
                else:
                    #host_dict[host] = "not_patched"
                    status = self.check_rma(host, session)
                    host_dict[host] = status

        except socket.error as error:
            host_dict[host] = "Down"
            print("Error on connect: %s" % error)
            socket_conn.close()
        except IOError as e:
            print("Ensure presence of path " + orbFile)
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
                if v == 'not_patched':
                    in_buffer.write("{0}".format(k) + ',')
                    logging.debug(in_buffer.getvalue())
                else:
                    if v == 'patched' or re.search(r'rma',v) or v == 'Down':
                        ex_buffer.write("{0} -  {1}".format(k, host_dict[k]) + '\n')
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

    def process(self, hosts, session):
        """
        This function will accept hostlist as input and call check_patchset function and store value in
        shared memory(Queue).
        :param hosts: A list of hosts
        :return: None
        """
        process_q = Queue()
        p_list = []
        for host in hosts:
            process_inst = Process(target=self.check_patchset, args=(host, session, process_q))
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
    parser.add_argument("-H", dest="hosts", required=True, help="The hosts in command line argument")
    parser.add_argument("--bundle", dest="bundle", required=True, help="Bundle name")
    parser.add_argument("--case", dest="case", required=True, help="Case number")
    parser.add_argument("--force", dest="force", action="store_true", help="Case number")
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    parser.add_argument("--encrypted_creds", help="Pass creds in via encrpyted named pipe")
    parser.add_argument("--decrypt_key", help="Used with --encrpyted_creds description")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    bundle = args.bundle
    hosts = args.hosts.split(',')
    case_no = args.case
    force = args.force
    if args.encrypted_creds:
        _,username,gpass = get_creds_from_km_pipe(pipe_file=args.encrypted_creds, decrypt_key_file=args.decrypt_key)
        try:
            client_id = config.get('GUS', 'client_id')
            client_secret = config.get('GUS', 'client_secret')
        except IOError:
            print("Can't read config file {0}".format(configdir + '/creds.config'))
            sys.exit(1)

    authObj = Auth(username,gpass,client_id,client_secret)
    session = authObj.login()
    class_object = HostsCheck(bundle, case_no, force)
    class_object.process(hosts, session)
    class_object.write_to_file()
    class_object.check_file_empty()

if __name__ == "__main__":
    main()
