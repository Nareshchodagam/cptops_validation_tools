#!/usr/bin/env python
from optparse import OptionParser
import logging
import socket
import re
import sys
from _socket import gaierror


def recvall(s):
    '''
    revcieve all data from socket until eof or the socket is closed
    '''
    BUFFER_SIZE = 2048
    data=[]
    while True:
        part = s.recv(BUFFER_SIZE)
        if not part: break
        data.append(part)
    return ''.join(data)

def getStat(host): 
    TCP_PORT = 2181
    MESSAGE = "stat"
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, TCP_PORT))
        s.send(MESSAGE)
        data = recvall(s)
        s.close()
        logging.debug(data)
        return data
    except gaierror:
        logging.error("%s does not exist. Please verify hostname is valid.", host)
        sys.exit(1)
    except socket.error as ex:
        logging.error("Exception occured on %s: %s", host, ex)
        return "SOCKET_ERROR"


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
    failure_count = 0
    if options.buildlist:
        hostlist =[]
        se = re.compile(r'(?<=[shared0|perfeng0]-searchzk)(\d)')
        host = socket.gethostname().split('.')[0]
        head, dc = host.split('-')[0::3]
        host_num = se.search(host)
        if host_num.group() == "2":
            for num in range(21, 26):
                hostlist.append("%s-searchzk%d-1-%s" % (head, num, dc))
        elif host_num.group() == "4":
             for num in range(41, 46):
                hostlist.append("%s-searchzk%d-1-%s" % (head, num, dc))
        logging.debug(hostlist)
    if options.hostlist:
        hostlist = options.hostlist.split(',')
    for h in hostlist:
        status = getStat(h)
        running = parseData(status)
        hosts_status[h] = running
    for h in hosts_status:
        if hosts_status[h] == False:
            print('Zookeeper is not running on %s' % h)
            failure_count += 1
            #sys.exit(1)
        else:
            print('Zookeeper is running on %s' % h)
    if failure_count > 1:
        logging.debug("Required nunber of available healthy servers is below threshold. Exiting...")
        sys.exit(1)
    elif failure_count == 1 and len(hostlist) == 1:
        logging.debug("Zookeeper does not appear to be running. Exiting...")
        sys.exit(1)
    else:
        sys.exit(0)
