from idbhost import Idbhost
from optparse import OptionParser
import socket
import logging
import re
import sys
import pprint
import os

def where_am_i():
    hostname = socket.gethostname()
    logging.debug(hostname)
    if re.search(r'internal.salesforce.com', hostname):
        short_site = 'sfm'
    else:  
        short_site = hostSplit(hostname)
    logging.debug(short_site)
    return short_site

def hostSplit(host):
    inst,hfuc,g,site = host.split('-')
    short_site = site.replace(".ops.sfdc.net", "")
    logging.debug(short_site)
    return inst,hfuc,g,short_site

def currentStatus(hosts, idb_mlist, status):
    for i in hosts:
        if i in idb_mlist:
            print("%s : Current : %s : Change to: %s" % (i, idb_mlist[i]['opsStatus_Host'],status))
            if idb_mlist[i]['opsStatus_Host'] == status:
                print("Current status %s and proposed status %s match. Exiting." % (idb_mlist[i]['opsStatus_Host'], status))
                sys.exit(0)
        
def setStatus(hosts, idb_mlist, status, user):
    
    currentStatus(hosts, idb.mlist,status)
    pp = pprint.PrettyPrinter(indent=4)
    #pp.pprint(idb.hjson)
    for i in hosts:
        _,_,_,dc = hostSplit(i)
        if i in idb_mlist:
            logging.debug(idb_mlist[i])
            str = ("/home/sfdc/current/dca-inventory-action/dca-inventory-action/inventory-action.pl \
-action update -resource host -name %s -cluster.name %s \
-cluster.superpod.name %s -cluster.superpod.dataCenter.name %s \
-updateFields modifiedBy=%s,operationalStatus=%s" %(i, idb_mlist[i]['clustername'],idb_mlist[i]['superpod'],dc,user,status))
            print(str)



if __name__ == '__main__':
    usage = """
    Code to check host details from idb

    %prog -H hostname [-v]    
    %prog -H ops-monitor1-1-was

    """
    parser = OptionParser(usage)
    parser.add_option("-s", "--status", dest="status",
                            help="The status to set the host to in iDB")
    parser.add_option("-u", "--user", dest="krbuser",
                            help="Kerb user if different from SSO")
    parser.add_option("-H", "--hosts", dest="hosts",
                            help="The host[s] in comma seperated format")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity") # will set to False later
    (options, args) = parser.parse_args()
    if options.hosts is None:
        parser.print_help()
        exit(-1)
    
    if options.krbuser:
        user = options.krbuser
    else:
        user = os.environ['USER']

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    site=where_am_i()
    if site == 'sfm':
        idb=Idbhost()
    else:
        idb=Idbhost(site)
    hosts=options.hosts.split(',')
    idb.gethost(hosts)    
    setStatus(hosts, idb.mlist, options.status,user)
