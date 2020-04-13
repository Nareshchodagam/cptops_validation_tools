#!/usr/bin/python
import socket
from optparse import OptionParser
import logging
import time
import sys
import threading
import Queue
import re
from datetime import datetime

if "/opt/sfdc/python27/lib/python2.7/site-packages" in sys.path:
    sys.path.remove("/opt/sfdc/python27/lib/python2.7/site-packages")

from os import path, environ
import getpass
import ConfigParser

sys.path.append('/opt/cpt/')
from GUS.base import Auth
from GUS.base import Gus

CONFIGDIR = environ['HOME'] + "/.cptops/config"
config = ConfigParser.ConfigParser()
hostname = socket.gethostname()
user_name = environ.get('USER')

if re.search(r'(sfdc.net)', hostname):
    sys.path.append("/opt/cpt/km")
    from katzmeow import get_creds_from_km_pipe
    try:
        import synnerUtil
    except ImportError:
        logging.error("Error: synnerUtil.py is not found under /opt/cpt/bin/. Try updating cpt-tools or get the file from CPT's codebase")
        sys.exit(1)

class ThreadHosts(threading.Thread):
    """Threaded check hosts sshable"""
    def __init__(self, queue, hosts_completed):
        threading.Thread.__init__(self)
        self.queue = queue
        self.hosts_completed = hosts_completed

    def run(self):
        while True:
            host,ncount = self.queue.get()
            result = check_host_up(host,ncount)
            logging.debug(result)
            if result == False:
                self.queue.task_done()
                self.hosts_completed[host] = False
                break
            self.hosts_completed[host] = True
            self.queue.task_done()


def check_ssh(ip):
    result = False
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, 22))
        result = True
    except socket.error as e:
        print "Error on connect: %s" % e
    s.close()
    return result

def get_ip(host):
    ip = socket.gethostbyname(host)
    return ip

def check_host_up(host,ncount):
    ip = get_ip(host)
    result = False
    seconds = 10
    count = 0
    delay = int(options.delay)
    print("Pausing checking for %s seconds while %s shuts down." % (delay,host))
    time.sleep(delay)
    while result != True:
        if count == ncount:
            print("Not able to connect to %s. Exiting" % host)
            return result
            sys.exit(1)
        result = check_ssh(ip)
        if result is True:
            break
        print("Retrying %s in %s seconds" % (host,seconds))
        time.sleep(seconds)
        count += 1
    print("System %s is up. Able to connect" % host)
    return result

def find_proxy(hostname):
    """
    This function is to find proxy for internal DCs <W-3758595>
    :param hostname: hostname
    :type hostname: str
    :return: Nothing
    :rtype: None
    """
    site = hostname.split('.')[0].split('-')[3]
    if re.search(r'rz1|crz|crd|chx|wax', site, re.IGNORECASE):
        environ['https_proxy'] = "http://public-proxy1-0-{0}.data.sfdc.net:8080/".format(site)
    else:
        environ['https_proxy'] = "http://public0-proxy1-0-{0}.data.sfdc.net:8080/".format(site)
        logging.debug("env variable set for prd host")
    # logger.debug("setup proxy %s" .format(environ['https_proxy']))

def update_patching_lh(host, session, gus_conn):
    lh_details = gus_conn.get_logical_host_id(session, host)

    try:
        host_id = lh_details['records'][0]['Id']
        logging.debug("Logical Host {0} Id is {1} ".format(host, host_id))
    except IndexError:
        logging.error("Error occured while fetching details for host {0}".format(host))

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y")
    patch_issue_full = "{};HostDown.PostPatch".format(str(dt_string))

    payload = {
        'Patch_Issue__c': patch_issue_full
    }

    ret = gus_conn.update_patching_lh(session, payload, host_id)
    if ret.status_code == 204:
        logging.info("Updated GUS Logical_host field for host {0} ".format(host))
    else:
        logging.error("Update to GUS failed for host {0} ".format(host))


if __name__ == "__main__":
    usage = """
    This code will check if a host is sshable for reconnection during automated work.

    %prog [-v] -H host(s)

    %prog -l=H shared-nfs1-1-was,shared-nfs1-2-was
    """
    parser = OptionParser(usage)
    parser.add_option("-H", "--hostlist", dest="hostlist", help="The comma seperated list of hosts to check")
    parser.add_option("-d", "--delay", dest="delay", default=120, type='int', help="The pause to delay while host reboots")
    parser.add_option("-c", "--ncount", dest="ncount", default=30, type='int', help="The pause to delay host n*10")
    parser.add_option("-v", action="store_true", dest="verbose", help="verbosity")
    parser.add_option("--encrypted_creds", dest="encrypted_creds", help="Pass creds in via encrypted named pipe")
    parser.add_option("--decrypt_key", dest="decrypt_key", help="Used with --encrypted_creds description")
    (options, args) = parser.parse_args()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if options.encrypted_creds:
        try:
            _, username, gpass = get_creds_from_km_pipe(pipe_file=options.encrypted_creds, decrypt_key_file=options.decrypt_key)
            username = username.split('@')[0]
        except ImportError as e:
            print("Import failed from GUS module, %s" % e)
            sys.exit(1)
    else :
        #kpass = getpass.getpass("Enter your kerberos password: ")
        gpass = getpass.getpass("Enter your GUS password: ")

    if options.hostlist is None:
        print(usage)
        sys.exit()

    try:
        config.readfp(open(CONFIGDIR + '/creds.config'))
    except IOError:
        logging.error("No creds.config file found")
        sys.exit(1)
    try:
        username = config.get('GUS', 'username')
        client_id = config.get('GUS', 'client_id')
        client_secret = config.get('GUS', 'client_secret')
    except ConfigParser.Error:
        logging.error('Problem getting username, client_id or client_secret')
        sys.exit(1)

    find_proxy(hostname)
    gus_conn = Gus()
    auth_obj = Auth(username, gpass, client_id, client_secret)
    session = auth_obj.login()

    if options.hostlist:
        hosts_completed = {}
        hosts = options.hostlist.split(',')
        queue = Queue.Queue()
        for i in range(20):
            t = ThreadHosts(queue, hosts_completed)
            t.setDaemon(True)
            t.start()

        for host in hosts:
            lst = [host, options.ncount]
            queue.put(lst)

        queue.join()

        flag = False
        logging.debug(hosts_completed)
        for key in hosts_completed:
            if hosts_completed[key] == False:
                update_patching_lh(key, session, gus_conn)
                flag = True
        
        print(hosts_completed)
        if flag:
            print('Error with one of the hosts')
            sys.exit(1)
