from idbhost import Idbhost
from optparse import OptionParser
import socket
import logging
import re

def where_am_i():
    hostname = socket.gethostname()
    logging.debug(hostname)
    if re.search(r'internal.salesforce.com', hostname):
        short_site = 'sfm'
    else:
        inst,hfuc,g,site = hostname.split('-')
        short_site = site.replace(".ops.sfdc.net", "")
    logging.debug(short_site)
    return short_site


def idb_status(hosts, *keys):
    for i in hosts:
        if i in idb.mlist:
            print(i)
            for key in keys:
                if idb.mlist[i][key]:
                    print("%s == %s" % (key, idb.mlist[i][key]))
            print('-'*10)
        else:
            print("No details for host in iDB %s" % i)
            print('-'*10)



if __name__ == '__main__':
    usage = """
    Code to check host details from idb

    %prog -H hostname [-v]    
    %prog -H ops-monitor1-1-was

    """
    parser = OptionParser(usage)
    parser.add_option("-c", "--case", dest="caseNum",
                            help="The case number(s) of the case to attach the file ")
    parser.add_option("-H", "--hosts", dest="hosts",
                            help="The case number(s) of the case to attach the file ")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity") # will set to False later
    (options, args) = parser.parse_args()
    if options.hosts is None:
        parser.print_help()
        exit(-1)


    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    site=where_am_i()
    if site == 'sfm':
        idb=Idbhost()
    else:
        idb=Idbhost(site)
    hosts=options.hosts.split(',')
    idb.gethost(hosts)
    #for i in hosts:
    #    if i in idb.mlist:
    #        if idb.mlist[i]['monitor-host']:
    #            print("%s == %s" % (i, idb.mlist[i]['monitor-host']))
    #        if idb.mlist[i]:
    #            print("%s == %s" % (i, idb.mlist[i]))
    #    else:
    #        print("No details for %s" % i)

    idb_status(hosts, 'monitor-host', 'opsStatus_Host', 'opsStatus_Cluster')
