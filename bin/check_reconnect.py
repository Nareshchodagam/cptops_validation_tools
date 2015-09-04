#!/usr/bin/python
import socket
from optparse import OptionParser
import logging
import time
import sys
import threading
import Queue
import common



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

if __name__ == "__main__":
    usage = """
    This code will check if a host is sshable for reconnection during automated work.

    %prog [-v] -H host(s)

    %prog -l=H shared-nfs1-1-was,shared-nfs1-2-was
    """
    parser = OptionParser(usage)
    parser.add_option("-H", "--hostlist", dest="hostlist",
                        help="The comma seperated list of hosts to check")
    parser.add_option("-d", "--delay", dest="delay", default=120, type='int',
                        help="The pause to delay while host reboots")
    parser.add_option("-c", "--ncount", dest="ncount", default=60, type='int',
                        help="The pause to delay host n*10")
    parser.add_option("-v", action="store_true", dest="verbose", help="verbosity")
    (options, args) = parser.parse_args()



    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    if options.hostlist is None:
        print(usage)
        sys.exit()

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

        logging.debug(hosts_completed)
        for key in hosts_completed:
            if hosts_completed[key] == False:
                print('Error with one of the hosts')
                print(hosts_completed)
                sys.exit(1)
        print(hosts_completed)