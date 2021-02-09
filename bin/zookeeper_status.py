#!/opt/sfdc/python27/bin/python
from optparse import OptionParser
import logging
import socket
import re
import sys
import os
import json
from _socket import gaierror

def recvall(s):
    '''
    receive all data from socket until eof or the socket is closed
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
        logging.debug(host)
        logging.debug(data)
        return data
    except gaierror:
        logging.error("%s does not exist. Please verify hostname is valid.", host)
        sys.exit(1)
    except socket.error as ex:
        logging.error("Exception occured on %s: %s", host, ex)
        return "SOCKET_ERROR"

def configQuorumStatus(zoocfgpath):
    status = {}
    if os.path.exists(zoocfgpath):
        zoo_config = open(zoocfgpath, 'r').read()
        healthyMembers = 0
        memberCount = 0
        for line in zoo_config.split(chr(10)):
            if line[:7] == 'server.':
                memberCount += 1
                host = line.split('=')[1].split(':')[0]
                if getStat(host).find('Zookeeper') != -1:
                    healthyMembers += 1
        status = {
            "QuorumStatus": "",
            "HealthyMembers": healthyMembers,
            "MemberCount": memberCount
        }
        if memberCount == 0:
            status["QuorumStatus"] = "INDETERMINATE - SUPPLIED ZOO.ZFG HAS NO QUORUM MEMBERS"
        else:
            if healthyMembers == memberCount:
                status["QuorumStatus"] = "HEALTHY"
            else:
                status["QuorumStatus"] = str(memberCount - healthyMembers) + "FAILED NODE(S)"
    else:
        status["QuorumStatus"] = "INDETERMINATE - ZOO.CFG PATH NOT FOUND"
    print(status)
    if status["QuorumStatus"] != "HEALTHY":
        sys.exit(1)

def configQuorumStatusByDC(datacenterjsonpath):
    status = {}
    host = os.getenv("HOSTNAME")
    _, dc = host.split('-')[0::3]
    dc = dc.split(".")[0]
    print(dc)
    if os.path.exists(datacenterjsonpath):
        jsonstr = open(datacenterjsonpath, 'r').read()
        datacenterConfig = json.loads(jsonstr)
        zkHosts = datacenterConfig["DcMap"][dc]["ZkHosts"]
        healthyMembers = 0
        memberCount = 0
        for zkhost in zkHosts.split(","):
            memberCount += 1
            if getStat(zkhost).find('Zookeeper') != -1:
                healthyMembers += 1
        
        status = {
            "QuorumStatus": "",
            "HealthyMembers": healthyMembers,
            "MemberCount": memberCount
        }
        if memberCount == 0:
            status["QuorumStatus"] = "INDETERMINATE - SUPPLIED DATA_CENTER.JSON HAS NO QUORUM MEMBERS"
        else:
            if healthyMembers == memberCount:
                status["QuorumStatus"] = "HEALTHY"
            else:
                status["QuorumStatus"] = str(memberCount - healthyMembers) + "FAILED NODE(S)"
    else:
        status["QuorumStatus"] = "INDETERMINATE - DATA_CENTER.JSON PATH NOT FOUND"
    print(status)
    if status["QuorumStatus"] != "HEALTHY":
        sys.exit(1)

def parseData(data):
    running = False
    for d in data.split('\n'):
        if re.match(r'Mode: (leader|follower)', d):
            logging.debug(d)
            running = True
    return running

def getLeader(data):
    zkleader = False
    for d in data.split('\n'):
        if re.match(r'Mode: leader', d):
            logging.debug(d)
            zkleader = True
    return zkleader

def create_list(case_list, master_list):
    '''
    Function to modify the existing hostlist.
    :return:
    '''
    active_host = get_current(case_list)
    if active_host == "":
        with open(master_list, 'r') as master, open(case_list, 'w') as case:
            raw_data = json.load(master)
            case.write(raw_data['follower'][0])
        sys.exit(0)
    else:
        rebuild_list(case_list, master_list, active_host)


def rebuild_list(case_list, master_list, active_host):
    '''
    :param case_list:
    :param master_list:
    :return:
    '''
    with open(master_list, 'r') as master:
        raw_data = json.load(master)

    try:
        index = raw_data['follower'].index(active_host)
        raw_data['follower'].pop(index)
    except ValueError:
        print "No More servers to process"
        cleanup(case_list, master_list)
        sys.exit(0)
    fh = open(master_list, 'w')
    json.dump(raw_data, fh)
    fh.close()
    if len(raw_data['follower']) != 0:
        fh = open(case_list, 'w')
        fh.write(raw_data['follower'][0])
        fh.close
    else:
        fh = open(case_list, 'w')
        fh.write(raw_data['leader'][0])
        fh.close

    return master_list

def get_current(case_list):
    '''
    Function to get the current host.
    :return:
    '''
    try:
        fh = open(case_list, 'r')
        curr_host = fh.readline().rstrip("\n")
        fh.close()
    except IOError:
        curr_host = ""
    return curr_host

def cleanup(case_list, master_list):
    '''
    Remove all files created by program.
    :return:
    '''
    os.remove(case_list)
    os.remove(master_list)

if __name__ == '__main__':
    usage = """
    Script checking zookeeper status    
    """
    parser = OptionParser(usage)

    parser.add_option("--quorumstatus", dest="quorumstatus", help="Path to zoo.cfg for assessing quorum health.")
    parser.add_option("--quorumstatusjson", dest="quorumstatusjson", help="Path to datacenter.json for assessing quorum health.")
    parser.add_option("-H", "--hostlist", dest="hostlist", help="The hostlist for the change")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity") # will set to False later
    parser.add_option("-b", action="store_true", dest="buildlist", default=False, help="Builds hostlist for Search Zookeeper.")
    parser.add_option("--byleader", dest="byleader", action="store_true", default="False", help="Patch servers by leader.")
    parser.add_option("-c", "--case_num", dest="casenum", help="Case number.")
    parser.add_option("-u", "--update", dest="update", action="store_true", help="Update caselist")
    parser.add_option("-r", dest="role", help="Role")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    if options.quorumstatus:
        configQuorumStatus(options.quorumstatus)
    if options.quorumstatusjson:
        configQuorumStatusByDC(options.quorumstatusjson)
    hostlist = ['localhost']
    hosts_status = {}
    failure_count = 0
    max_allowed_fails = 1
    if options.buildlist and options.role:
        hostlist =[]
        se = re.compile(r'(?<=[shared0|perfeng0]-searchzk)(\d)')
        host = socket.gethostname().split('.')[0]
        head, dc = host.split('-')[0::3]
        host_num = se.search(host)
        if options.role == "smszk":
            if "smszkdev" in host:
                max_allowed_fails = 0
                for num in range(1, 6):
                    hostlist.append("sec0-smszkdev%d-1-%s" % (num, dc))
            elif "smszk" in host:
                max_allowed_fails = 0
                for num in range(1, 6):
                    hostlist.append("sec0-smszk%d-1-%s" % (num, dc))
        elif options.role == "smszkdev":
            max_allowed_fails = 0
            for num in range(1, 6):
                hostlist.append("sec0-smszkdev%d-1-%s" % (num, dc))
        elif options.role == "searchzk":
            if host_num.group() == "2":
                for num in range(21, 26):
                    hostlist.append("%s-searchzk%d-1-%s" % (head, num, dc))
            elif host_num.group() == "4":
                 for num in range(41, 46):
                    hostlist.append("%s-searchzk%d-1-%s" % (head, num, dc))
        logging.debug(hostlist)

    if options.update == True:
        case_list = "{}/{}_include".format(os.path.expanduser('~'), options.casenum)
        master_list = "{}/{}_master".format(os.path.expanduser('~'), options.casenum)
        create_list(case_list, master_list)
        sys.exit(0)

    if options.hostlist and options.byleader == True:
        case_list = "{}/{}_include".format(os.path.expanduser('~'), options.casenum)
        master_list = "{}/{}_master".format(os.path.expanduser('~'), options.casenum)
        zkcluster={"follower": [], "leader": []}
        hostlist = options.hostlist.split(',')
        for h in hostlist:
            status = getStat(h)
            zkleader = getLeader(status)
            if zkleader == True:
                logging.debug(h)
                zkcluster['leader'].append(h)
            else:
                zkcluster['follower'].append(h)
        with open(master_list, 'w') as master:
            data = json.dumps(zkcluster)
            master.write(data)
            master.close()
        create_list(case_list, master_list)
        sys.exit(0)
    if options.hostlist and options.byleader == False:
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
    if failure_count > max_allowed_fails:
        logging.debug("Required nunber of available healthy servers is below threshold. Exiting...")
        sys.exit(1)
    elif failure_count == 1 and len(hostlist) == 1:
        logging.debug("Zookeeper does not appear to be running. Exiting...")
        sys.exit(1)
    else:
        sys.exit(0)
