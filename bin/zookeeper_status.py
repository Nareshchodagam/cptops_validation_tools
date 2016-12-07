#!/usr/bin/env python
#from common import Common 
from optparse import OptionParser
import logging
import socket
import re
import sys
from _socket import gaierror


def getStat(host): 
    TCP_PORT = 2181
    BUFFER_SIZE = 1024
    MESSAGE = "stat"
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, TCP_PORT))
        s.send(MESSAGE)
        data = s.recv(BUFFER_SIZE)
        s.close()
        logging.debug(data)
        return data
    except gaierror:
        logging.error("%s does not exist. Please verify hostname is valid.", host)
        sys.exit(1)

def parseData(data):
    running = False
    for d in data.split('\n'):
        if re.match(r'Mode: (leader|follower)', d):
            logging.debug(d)
            running = True
    return running
            
            

if __name__ == '__main__':
    usage = """
    Script checking zookeeper status    
    """
    parser = OptionParser(usage)
   
    parser.add_option("-H", "--hostlist", dest="hostlist", help="The hostlist for the change")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity") # will set to False later
    parser.add_option("-b", action="store_true", dest="buildlist", default=False, help="Builds hostlist for Search Zookeeper.")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    hostlist = ['localhost']
    hosts_status = {}
    if options.buildlist:
        hostlist =[]
        se = re.compile(r'(?<=[shared0|perfeng0]-searchzk)(\d)')
        host = socket.gethostname().split('.')[0]
        head, dc = host.split('-')[0::3]
        host_num = se.search(host)
        if host_num.group() == "2":
            for num in range(21, 26):
                hostlist.append("%s-searchzk%d-1-%s" % (head, num, dc))
                print hostlist
                exit(0)
        elif host_num.group() == "4":
             for num in range(41, 46):
                hostlist.append("%s-searchzk%d-1-%s" % (head, num, dc))
                print hostlist
                exit(0)
    if options.hostlist:
        hostlist = options.hostlist.split(',')
    for h in hostlist:
        status = getStat(h)
        running = parseData(status)
        hosts_status[h] = running
    for h in hosts_status:
        if hosts_status[h] == False:
            print('Zookeeper is not running on %s' % h)
            sys.exit(1)
        else:
            print('Zookeeper is running on %s' % h)
    sys.exit(0)