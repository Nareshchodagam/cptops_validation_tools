#!/usr/bin/python
# Script creates a batch file for the host sumbitted. So they can be used
# with gigantor batch executions. 
#
import os
from idbhost import Idbhost
from optparse import OptionParser
import logging
import re
from socket import gethostname
import sys


def idb_connect(site):
    """
    Initiate connection to idb based on the site/DC name.

    :param site: The site name
    :type site: string
    :return: This function will return a class instance.
    :rtype:  Instance

    """
    try:
        logging.debug('Connecting to CIDB')
        user = pswd = None
        if options.encrypted_creds:
            sys.path.append("/opt/cpt/")
            try:
                from km.katzmeow import get_password_from_km_pipe
                import getpass
                user =  getpass.getuser()
                pswd = get_password_from_km_pipe(pipe_file=options.encrypted_creds, decrypt_key_file=options.decrypt_key)
                logging.debug("decoded creds passed by km")
            except ImportError:
                logging.error("could not import the km module, will not decode creds passed in by km")
        idb=Idbhost(site=site, user=user, pswd=pswd)
        return idb
    except:
        print("Unable to connect to idb")
        sys.exit(1)

def where_am_i():
    """
    This function will extract the DC/site name form where you are executing your code.

    :param: This function doesn't require any parameter to pass.
    :return: This function will return the side/DC name e.g sfm/chi/was/tyo etc....
    """
    hostname = gethostname()
    logging.debug(hostname)
    if not re.search(r'(sfdc.net|salesforce.com)', hostname):
        short_site = 'sfm'
    elif re.search(r'internal.salesforce.com', hostname):
        short_site = 'sfm'
    else:
        inst, hfuc, g, site = hostname.split('-')
        short_site = site.replace(".ops.sfdc.net", "")
    logging.debug(short_site)
    return short_site

if __name__ == "__main__":
    usage='%(prog)s -H <host_list> -d <datacenter>'
    parser = OptionParser(usage)
    parser.add_option("-H", dest="hosts", help="The hosts in command line argument")
    parser.add_option("-d", dest="datacenter", help="datacenter")
    parser.add_option("--file", dest="filename", default="batch.list", help="batch filename.")
    parser.add_option("--encrypted_creds",dest="encrypted_creds", help="Pass creds in via encrpyted named pipe; used by katzmeow")
    parser.add_option("--decrypt_key", dest="decrypt_key", help="Used only with --encrpyted_creds")
    (options, args) = parser.parse_args()
    
    legacy_dcs = ["chi", "was", "tyo", "lon", "asg"]
    if options.datacenter in legacy_dcs:
        hoststring = "HOSTSTRING"
    else:
        hoststring = "HOST"
        
    '''
    Create the batch list
    '''
    
    file_batch = open(os.environ['HOME'] + "/" + options.filename, 'w')
    file_batch.write("{0},DEVICEROLE,SERIAL_NUMBER\n".format(hoststring))
    site = where_am_i()
    idb = idb_connect(site)   
    idb.gethost(options.hosts)
    for host in idb.mlist.iterkeys():
       file_batch.write("{0},{1},{2}\n".format(host, idb.mlist[host]['deviceRole'], idb.mlist[host]['Serial Number']))
    file_batch.close()
