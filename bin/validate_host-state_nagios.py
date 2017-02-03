#!/usr/bin/python
"""
Purpose - Script to check the state of a service from Nagios and to hit the given port.
date - 01-08-2015
version - 1.0
"""

# Imports
import sys
import socket
import xml.etree.ElementTree as ET
import urllib2
import urllib
import json
import re
from idbhost import Idbhost
import logging
from argparse import ArgumentParser


# Global Variables
'''This file is located on the ops-release*-<site> hosts to allow release_runner to enable/disable monitoring'''
passwd_file = '/home/sfdc/current/releaserunner/releaserunner/test-manual-execution/testFiles/secure_test.xml'

# Function to extract Nagios credentials


def get_nagios_creds(filename):
    naguser = None
    nagpass = None
    try:
        tree = ET.ElementTree(file=filename)
        root = tree.getroot()
        for elem in tree.iter():
            if elem.tag == 'nagios_user':
                naguser = elem.text
            if elem.tag == 'nagios_passwd':
                nagpass = elem.text
        return naguser, nagpass
    except Exception as e:
        logging.error("Something went wrong getting the nagios creds: %s" % e)
        sys.exit(1)


# Function to check the port on remote host
def check_port(host, port):
    result = False
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
        result = True
    except socket.error as e:
        print "Error on connect: %s" % e
    s.close()
    return result


# Function to get the DC name
def where_am_i():
    hostname = socket.gethostname()
    logging.debug(hostname)
    inst, hfuc, g, site = hostname.split('-')
    short_site = site.replace(".ops.sfdc.net", "")
    logging.debug(short_site)
    return short_site

# Function to get the instance, hostfunc and dc


def get_inst_site(host):
    inst, hfunc, g, site = host.split('-')
    short_site = site.replace(".ops.sfdc.net", "")
    return inst, hfunc, site


# Function to get the monitor host from iDB, if not build it from hostname
def get_monitor_host(hosts):
    site = where_am_i()
    idb = Idbhost(site)
    idb.gethost(hosts)
    logging.debug(idb.mlist)
    mhs = {}
    m_h = 0
    sp_mon = {'0': 'ops0-monitor-', '1': 'ops-monitor-', '2': 'ops-monitor-',\
              '3': 'ops-monitor30-', '4': 'ops0-monitor-'}
    for h in hosts:
        if h in idb.mlist:
            idb_m_h = idb.mlist[h]['monitor-host']
            idb_m_h = idb_m_h.replace(".ops.sfdc.net", "")
            if idb_m_h == 'no host' or idb_m_h is None:
                print("No monitor host in idb for %s" % h)
            else:
                m_h = idb_m_h
        else:
            inst, hfunc, dc = get_inst_site(h)
            if re.search(r'na|cs|gs|eu|ap', inst):
                m_h = inst + '-monitor-' + dc
            else:
                m = re.search(r'(\d)$', inst)
                g = re.search(r'(3\d)$', hfunc)
                if m:
                    sp = m.group(1)
                    m_h = sp_mon[sp] + dc
                elif g:
                    sp = '3'
                    m_h = sp_mon[sp] + dc
                else:
                    m_h = 'ops-monitor-' + dc
        mhs[h] = m_h
    return mhs


# Function to run the Nagios query
def run_nagios_query(cmd, host, monitor, user, passwd, state):
    values = {'query': cmd, 'hostname': host, 'servicedescription': state}

    # create a password manager
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()

    # Add the username and password.
    # If we knew the realm, we could use it instead of None.
    top_level_url = 'http://'+monitor+'.ops.sfdc.net/nagios'
    password_mgr.add_password(None, top_level_url, user, passwd)
    handler = urllib2.HTTPBasicAuthHandler(password_mgr)
    url = top_level_url + '/cgi-bin/statusjson.cgi'
    logging.debug(url)

    # create "opener" (OpenerDirector instance)
    opener = urllib2.build_opener(handler)
    data = urllib.urlencode(values)
    response = opener.open(url, data)
    json_data = json.loads(response.read())
    logging.debug(json_data)

    logging.debug(response.read())
    rcode = response.code
    return json_data



if __name__ == "__main__":
    usage = """

    python %prog -H [hostnames]  -S [service_name] -P [port to check]


    Check the monitoring of hosts
    python validate_monhost.py -H umps1-sshare1-1-sjl,umps2-prsn1-1-sjl -S Chatternow-Dstore-STATE -P 8087


    This script checks if monitoring has been setup or not. If monitor host is
    not defined in iDB, it will try to construct the monitor hostname from
    the target hostname.

    """
    parser = ArgumentParser(usage)
    parser.add_argument("-H", "--hostname", dest="hostname", action="store", help="Target hostname")
    parser.add_argument("-S", "--services", action="store", dest="svc_desc", help="The service name")
    parser.add_argument("-P", "--port", dest="port", action="store", type=int, help="Port to check the connectivity")
    parser.add_argument("-V", "--verbose", action="store_true", dest="verbose", help="Set verbosity to debug level.")

    args = parser.parse_args()
    naguser, nagpasswd = get_nagios_creds(passwd_file)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if args.hostname is None or args.svc_desc is None or args.port is None:
        print(usage)

    else:
        hosts = args.hostname.split(',')
        monhosts = get_monitor_host(hosts)
        svc_status = dict()
        for host in hosts:
            json_response = run_nagios_query('service', host, monhosts[host], naguser, nagpasswd, args.svc_desc)
            if json_response['result']['type_text'] == "Success" and json_response['result']['type_code'] == 0:
                print(host + " == " + json_response['data']['service']['plugin_output'])
                svc_status[host] = json_response['data']['service']['status']
                if svc_status[host] == 2:
                    pass
                else:
                    print("May be passive check is stale, Checking on port %s"%args.port)
                    result = check_port(host, args.port)
                    if result is True:
                        print("Port %s is up and running"%args.port)
                    else:
                        sys.exit(1)
            else:
                print("Please verify the service name")
                sys.exit(1)
