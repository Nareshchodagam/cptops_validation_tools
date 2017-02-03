#!/usr/bin/env python
"""
    Generates a host list from input. Excludes any hosts found in the exclude list and filters for a host regex.
"""
from optparse import OptionParser
import json
import urllib2
import logging
import re
import glob
import os.path
import logging
import pprint
from common import Common
from idbhost import Idbhost
#from buildplan_helper import Buildplan_helper
import sys
#reload(sys)

iDBurl = {'asg': "https://inventorydb1-0-asg.data.sfdc.net/api/1.03",
          'chi': "https://inventorydb1-0-chi.data.sfdc.net/api/1.03",
          'chx': "https://inventorydb1-0-chx.data.sfdc.net/api/1.03",
          'lon': "https://inventorydb1-0-lon.data.sfdc.net/api/1.03",
          'sfm': "https://inventorydb1-0-sfm.data.sfdc.net/api/1.03",
          'sjl': "https://inventorydb1-0-sjl.data.sfdc.net/api/1.03",
          'tyo': "https://inventorydb1-0-tyo.data.sfdc.net/api/1.03",
          'was': "https://inventorydb1-0-was.data.sfdc.net/api/1.03",
          'wax': "https://inventorydb1-0-wax.data.sfdc.net/api/1.03",
          'frf': "https://inventorydb1-0-frf.data.sfdc.net/api/1.03",
          'phx': "https://inventorydb1-0-phx.data.sfdc.net/api/1.03",
          'dfw': "https://inventorydb1-0-dfw.data.sfdc.net/api/1.03",
          'cidb': "https://cidb1-0-sfm.data.sfdc.net/cidb-api/1.03",
          }

def idb_connect():
    try:
        logging.debug('Connecting to CIDB')
        idb = Idbhost()
        return idb
    except:
        print "Unable to connect to idb"
        exit()
        
def gen_request(reststring, cidblocal=False, derivedc=''):
    # Build the API URL
    dc = derivedc.lower()
    if cidblocal:
        # CIDB URL is slightly different, so it needs to be cut up and
        # reassembled.
        derivever = iDBurl['cidb'].split('/')[4]
        derivemethod = iDBurl['cidb'].split('/')[0]
        derivehost = iDBurl['cidb'].split('/')[2]
        derivepath = iDBurl['cidb'].split('/')[3]
        url = derivemethod + '//' + derivehost + '/' + \
        derivepath + '/' + dc + '/' + derivever + reststring
        # Use the java cli tool to sign the CIDB request and return a
        # keyed URL.
        url = os.popen('java -jar ' + common.cidb_jar_path + '/cidb-security-client-0.0.7.jar ' + common.cidb_jar_path + '/keyrepo "' + url + '"').read()
    else:
        url = iDBurl[dc] + reststring

    logging.debug(url)

    # Send the request.
    r = urllib2.urlopen(url)
    # use the data.
    data = json.load(r)
    logging.debug(data)
    logging.debug(data['total'])
    if data['total'] == 1000:
        raise Exception('idb record limit of 1000, you may be missing records')

    return data

def cacher(current_obj, arglist):
    # loop through fields from left to right caching ibased on JacksonId if they point to a json object returning if they are cached
    for arg in arglist:
        if type(current_obj[arg]) is unicode:
          current_obj = cache[current_obj[arg]]
        else:
          current_obj = current_obj[arg]
          cache[current_obj['@' + arg + 'JacksonId']] = current_obj
    return current_obj

def get_hosts(dr,role,cluster,dc,cidblocal=True):
    hosts = []
    reststring = '/allhosts?operationalStatus=active&cluster.dr=' + str(dr).lower() + '&deviceRole=' + role + '&cluster.name=' + cluster + '&fields=name,deviceRole,failOverStatus,cluster.name,cluster.superpod.name&expand=cluster'
    current = gen_request(reststring, cidblocal, dc)
    logging.debug(current)
    if current['total'] > 0:
              for hval in current['data']:
    #              sptemp = cacher(hval, ['cluster', 'superpod'])['name']
                  hosts.append(hval['name'])
    return hosts

def validateInputDict(inputdict):
    logging.debug(inputdict)
    try:
        inputdict = json.loads(inputdict)
    except Exception as e:
        print("Not valid json : %s" % e)
        sys.exit(1)
    required = ['dr', 'role', 'cluster', 'dc']
    for i in required:
        if i not in inputdict:
            print('Missing %s from the input provided %s' % (i, inputdict))
            sys.exit(1)
    clusters = inputdict['cluster'].split(",")
    if len(clusters) != 1:
        print('Provided more then one cluster in input %s : %s' %(clusters, inputdict['cluster'])) 
        sys.exit(1)
    roles = inputdict['role'].split(",")
    if len(roles) != 1:
        print('Provided more then one role in input %s : %s' %(roles, inputdict['role'])) 
        sys.exit(1)
    return inputdict

def filteredHosts(hosts,hostfilter):
    logging.debug(hostfilter)
    filtered_hosts = [k for k in hosts if re.match(hostfilter, k)]
    return filtered_hosts

def writeHostlist(cluster,hosts):
    first_line = "HOSTS\n"
    s = '\n'.join(hosts)
    filename = cluster + ".hostlist"
    with open(filename, 'w') as f:
        f.write(first_line)
        f.write(s)
        f.write("\n")

def getExcludeHosts(excludelist):
    exclude_hosts = []
    if os.path.isfile(excludelist):
        try:
            with open(excludelist, 'r') as f:
                for l in f:
                    exclude_hosts.append(l.rstrip())        
        except Exception as e:
            print('Problem getting hosts to exclude from %s : %s' % (excludelist, e))
    
    return exclude_hosts

def excludeHosts(hosts,excludelist):
    exclude_hosts = getExcludeHosts(excludelist)
    logging.debug(exclude_hosts)
    for h in exclude_hosts:
        if h in hosts:
            i = hosts.index(h)
            del hosts[i]
    return hosts
if __name__ == "__main__":
    usage = """
    
    """
    parser = OptionParser(usage)
    excludefile = os.path.expanduser('~') + "/exclude_hosts.txt"
    parser.set_defaults(excludelist=excludefile)
    parser.add_option("-v", action="store_true", dest="verbose", default=False, \
                      help="verbosity")
    parser.add_option("-G", "--idbgen", dest="idbgen", help="generate from idb")
    parser.add_option("-e", "--excludelist", dest="excludelist", help="Exclude list file path")
    (options, args) = parser.parse_args()
    if options.verbose:
          logging.basicConfig(level=logging.DEBUG)  
    common = Common()
    cache = {}
    cidblocal=True
    hosts = ()
    
    
    if options.idbgen:
        inputdict = validateInputDict(options.idbgen)
        dr = inputdict['dr']
        role = inputdict['role']
        cluster = inputdict['cluster']
        dc = inputdict['dc']
        hosts = get_hosts(dr,role,cluster,dc,cidblocal)
        logging.debug(hosts)
        if inputdict['hostfilter']:
            hosts = filteredHosts(hosts, inputdict['hostfilter'])
        print(hosts)
        new_hosts = excludeHosts(hosts,options.excludelist)
        print(new_hosts)
        writeHostlist(cluster, hosts)
