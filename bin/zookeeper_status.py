#!/usr/bin/env python
#from common import Common 
from optparse import OptionParser
import logging
import socket
import re
import sys


def getStat(host): 
    TCP_PORT = 2181
    BUFFER_SIZE = 1024
    MESSAGE = "stat"
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, TCP_PORT))
    s.send(MESSAGE)
    data = s.recv(BUFFER_SIZE)
    s.close()
    logging.debug(data)
    return data

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
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    hostlist = ['localhost']
    hosts_status = {}
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