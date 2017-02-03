#!/usr/bin/python

"""Description: This script is written to check whether monitoring has setup
    on monitor  hosts."""

# Imports
import sys
import socket
import logging
from optparse import OptionParser
import xml.etree.ElementTree as ET
import urllib2
import urllib
import json
import re
from idbhost import Idbhost


# Global Variables
'''This file is located on the ops-release*-<site> hosts to allow \
    release_runner to enable/disable monitoring'''
passwd_file = '/home/sfdc/current/releaserunner/releaserunner/' \
              'test-manual-execution/testFiles/secure_test.xml'


# Function to extract the Nagios username and password
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


def run_nagios_query(cmd, host, monitor, user, passwd):
    values = {'query': cmd, 'hostname': host}

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


def get_host_list(devicerole):
    all_hosts = []
    site = where_am_i()
    roles = devicerole.split(',')
    idb = Idbhost(site)
    spoddata = idb.sp_data(site)
    spods = idb.sp_list
    pods = idb.spcl_grp

    for spods1, pod in pods.items():
        for values in pod.values():
            for val in values.split(','):
                idb.clustinfo(site, val)
                idb.deviceRoles(devicerole)
                all_hosts += idb.roles_all[val][devicerole]
    return all_hosts

if __name__ == "__main__":
    usage = """

    python %prog -H [hostnames]
    python %prog -r [devicerole]

    Check the monitoring of hosts
    python validate_monhost.py -H umps1-sshare1-1-sjl,umps2-prsn1-1-sjl

    Check the monitoring status of all the search servers
    python validate_monhost.py -r search

    This script checks if monitoring has been setup or not. If monitor host is
    not defined in iDB, it will try to construct the monitor hostname from
    the target hostname.

    """
    parser = OptionParser(usage)
    parser.add_option("-m", "--monitor-host", dest="monhost", action="store",
                      help="Monitor (nagios server) hostname")
    parser.add_option("-H", "--hostname", dest="hostname", action="store",
                      help="Target hostname")
    parser.add_option("-r", "--role", action="store", dest="devicerole",
                      help="The app role")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      default=False, help="Set verbosity to debug level.")
    (options, args) = parser.parse_args()
    naguser, nagpasswd = get_nagios_creds(passwd_file)

    if options.hostname is None and options.devicerole is None:
        print(usage)

    if options.hostname:
        hosts = options.hostname.split(',')
        monhosts = get_monitor_host(hosts)

        for host in hosts:
            json_response = run_nagios_query('host', host, monhosts[host],
                                             naguser, nagpasswd)
            if json_response['result']['type_text'] == "Success" and \
                    json_response['result']['type_code'] == 0:
                print("%s - YES" % host)
            else:
                print("%s - NO" % host)

    if options.devicerole:
        hosts = get_host_list(options.devicerole)
        monhosts = get_monitor_host(hosts)
        for host in hosts:
            json_response = run_nagios_query('host', host, monhosts[host],
                                             naguser, nagpasswd)
            if json_response['result']['type_text'] == "Success" and \
                    json_response['result']['type_code'] == 0:
                print("%s - YES" % host)
            else:
                print("%s - NO" % host)
    
