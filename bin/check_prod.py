#!/usr/bin/env python
import common
from idbhost import Idbhost
from optparse import OptionParser
import socket
import logging
import re
import subprocess
import sys

def where_am_i():
    """
    This code checks what location you are in based on hostname
    
    Returns the three letter site code
    
    Example output:
    was
    """
    hostname = socket.gethostname()
    logging.debug(hostname)
    if not re.search(r'(sfdc.net|salesforce.com)', hostname):
        short_site = 'sfm'
    elif re.search(r'internal.salesforce.com', hostname):
        short_site = 'sfm'
    else:
        inst,hfuc,g,site = hostname.split('-')
        short_site = site.replace(".ops.sfdc.net", "")
    logging.debug(short_site)
    return short_site

def getPriSec(pod_details,insts):
    """
    This function takes a dict containing instances per dc broken down 
    by SP and a list of instances to check  
    
    Returns a dict with the instances allocated to primary or secondary 
    """
    instsPROD = {}
    for inst in insts.split(','):
        instsPROD[inst] = None
        for sp in pod_details:
            logging.debug(pod_details[sp])
            if 'Primary' in pod_details[sp]:
                if inst in pod_details[sp]['Primary'].split(','):
                    logging.debug('found %s in Primary' % inst)
                    instsPROD[inst] = 'primary'
            if 'Secondary' in pod_details[sp]:
                if inst in pod_details[sp]['Secondary'].split(','):
                    logging.debug('found %s in Secondary' % inst)
                    instsPROD[inst] = 'secondary'
    return instsPROD

def validatePROD(details,loc):
    """
    Validates if a list of instances are 
    Input : a comma seperated list and a string to compare be it primary or secondary
    Returns : a dict containing instance and true or false based on location
    """
    logging.debug(details)
    loc_details = {}
    for d in details:
        logging.debug("%s %s %s" %(d,details[d],loc))
        if details[d] == None:
            loc_details[d] = False
        elif not re.match(loc, details[d], re.IGNORECASE) :
            loc_details[d] = False
        else:
            loc_details[d] = True
    logging.debug(loc_details)
    return loc_details


if __name__ == '__main__':
    usage = """
    Code to get pods of cluster types from idb

    %prog [-d comma seperated list of dc's short code] [-t cluster type of pod hbase etc] [-v]
    %prog -d asg [-v]   
    %prog -d asg,sjl,chi,was -t hbase

    """
    parser = OptionParser(usage)
    parser.set_defaults(status='active', type='pod')
    parser.add_option("-d", "--dc", dest="dc",
                            help="The dc(s) to get data for ")
    parser.add_option("-l", "--loc", dest="loc",
                            help="Are we working with PROD or DR")
    parser.add_option("-i", "--instances", dest="instances",
                            help="The SP status eg hw_provisioning or provisioning or active ")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity") # will set to False later
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    # Figure out the loation we're running form
    site=where_am_i()
    logging.debug(site)
    # Set the correct site code to create the object
    if site == 'sfm':
        idb=Idbhost()
    else:
        idb=Idbhost(site)
    # Get the active pods in a site 
    data = idb.sp_data(site, 'ACTIVE', 'pod')
    pod_details = idb.spcl_grp
    logging.debug(pod_details)
    if options.instances and options.loc:
        # Get the locations of each instance and confirm if primary or secondary
        pri_sec_details = getPriSec(pod_details,options.instances.upper())
        loc_details = validatePROD(pri_sec_details,options.loc)
        for inst in loc_details:
            print(loc_details[inst])
            if loc_details[inst] == False:
                print('%s is not %s in this DC, please review the instances' % (inst,options.loc))
                print('%s' % loc_details)
                sys.exit(1)
        sys.exit(0)
