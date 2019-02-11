#!/usr/bin/python
import socket
from optparse import OptionParser
import logging
import sys
import threading
import Queue
from subprocess import Popen, PIPE, CalledProcessError
from os import path

user_home = path.expanduser('~')

class ThreadHosts(threading.Thread):
    def __init__(self, queue):
        """
        :param queue: contains host
        """
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        """
        :return:
        """
        while True:
            host = self.queue.get()
            result = check_host_up(host)
            logging.debug(result)
            if result is False:
                Updater(host)
                logger.info("Updating iDB status for host {}".format(host))
                update_idb_status(host)
                if options.role == "ffx":
                    buddy_host = buddy_find(host)
                    logger.info("Updating iDB status for buddy host {}".format(buddy_host))
                    update_idb_status(buddy_host)
            else:
                logger.debug("host is up {}".format(host))
            self.queue.task_done()

def check_ssh(ip):
    """
    This function checks port 22 for hosts
    :param ip: ip of host
    :return: True|False
    """
    result = False
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    try:
        sock.connect((ip, 22))
        logger.debug(sock.connect((ip, 22)))
        result = True
    except socket.error as err:
        logger.debug(err)
    sock.close()
    return result

def get_ip(host):
    """
    This function returns ip of host
    :param host: hostname
    :return: ip
    """
    ip = socket.gethostbyname(host)
    return ip

def update_iDB(cmd):
    """
    This function updates iDB entry
    :param cmd: command to run
    :return: updated idb entry
    """
    try:
        command = Popen([cmd], stdout=PIPE, shell=True)
        (output, _) = command.communicate()
    except CalledProcessError as error:
        logger.error(error)
        exit(1)
    return output

def update_idb_status(host):
    """
    This host creates command for updating idb
    :param host: hostname
    :return:
    """
    cmd = "inventory-action.pl -use_krb_auth -resource host -name " + host + "  -action read | egrep -i 'operationalStatu'"
    output = update_iDB(cmd)
    if "IN_MAINTENANCE" in output:
        logger.debug("iDB host status IN_MAINTENANCE : {}".format(host))
    else:
        cmd = "inventory-action.pl -use_krb_auth -resource host -name " + host + "  -action update -updateFields operationalStatus=IN_MAINTENANCE"
        output = update_iDB(cmd)
        logger.debug(output)

def check_host_up(host):
    """
    This function check if server is online
    :param host: hostname
    :return: True|False
    """
    result = False
    ip = get_ip(host)
    result = check_ssh(ip)
    return result

def readfile(case):
    """
    This function reads host file
    :param case: caseNumber
    :return: contents of host file
    """
    filename = user_home + '/'+ case + "_include"
    with open(filename) as f:
        string_var = f.read()
    return string_var

def writefile(case, updated_host, downhost):
    """
    This function updates both include file and exclude file
    :param case: caseNumber
    :param updated_host: updated host list
    :return: updated host file
    """
    filename = user_home + '/' + case + "_include"
    with open(filename, 'w') as f:
        f.write(updated_host + "\n")
    excludefile = user_home + '/' + case + "_exclude"
    with open(excludefile, 'a') as f:
        f.write(downhost + " - IN_MAINTENANCE\n")

def Updater(item):
    """
    This function updates host list
    :param item: hostname
    :return:
    """
    #convert string to list
    string_var = readfile(options.case).rstrip()
    temp_list = set(string_var.split(','))
    #check if the list contains the item string
    if item in temp_list:
        temp_list.remove(item)
    else:
        logger.debug("{0}_include doesn't contains : {1}".format(options.case, item))
    updated_string = ((','.join(temp_list)))
    writefile(options.case, updated_string, item)

def buddy_find(host):
    """
    This function is used to check buddy host for ffx server.
    :param host: hostname to check the buddy
    :return: Buddy Host
    """
    hs = host.split('-')
    site, cluster, hostprefix, hostnum = hs[-1], hs[0], hs[1][-1], hs[2]
    if hostprefix == '1':
        buddyprefix = '2'
    elif hostprefix == '2':
        buddyprefix = '1'
    elif hostprefix == '5':
        buddyprefix = '6'
    elif hostprefix == '6':
        buddyprefix = '5'
    buddyhost = '%s-ffx%s-%s-%s' % (cluster, buddyprefix, hostnum, site)
    return buddyhost

if __name__ == "__main__":
    usage = """
    This code will update idb status IN_MAINTENANCE for down host"
    %prog [-v] -R role -C caseNumber -H host(s)
    """
    parser = OptionParser(usage)
    parser.add_option("-H", "--hostlist", dest="hostlist", help="The comma seperated list of hosts to check")
    parser.add_option("-v", action="store_true", dest="verbose", help="verbosity")
    parser.add_option("-C", "--case", dest="case", help="Case number")
    parser.add_option("-R", "--role", dest="role", help="role name")
    (options, args) = parser.parse_args()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    if options.hostlist:
        hosts = options.hostlist.split(',')
        queue = Queue.Queue()
        for i in range(20):
            t = ThreadHosts(queue)
            t.setDaemon(True)
            t.start()
        for host in hosts:
            queue.put(host)
        queue.join()
    else:
        logger.error("hostname required")
        sys.exit(1)
