#!/usr/bin/python
import os.path
import subprocess
import logging
import re
from optparse import OptionParser

def valid_ints(routes):
    #print(routes)
    ints = []
    for i in routes.splitlines():
        m = re.search(r'dev (eth\d)', i)
        if m:
            ints.append(m.group(1))
    return list(set(ints))

def live_routes(lst):
    route_ver = subprocess.Popen(lst, stdout=subprocess.PIPE)
    out, err = route_ver.communicate()
    return out

def check_routes_exist(interface):
    route_path = '/etc/sysconfig/network-scripts'
    filename = route_path + '/route-' + interface
    if os.path.isfile(filename):
        logging.debug(filename)
        with open(filename, 'r') as f:
            data = f.read()
            return data

def save_output(ints,int_routes_configured,current_routes,filename):
    with open(filename, 'w') as f:
        f.write('Interfaces\n')
        for i in ints:
            f.write(i + "\n")
        f.write('\n')
        f.write('Interfaces with configured routes\n')
        for i in int_routes_configured.keys():
            f.write(i + "\n")
            if int_routes_configured[i] == None:
                int_routes_configured[i] = 'Empty'
            f.write(int_routes_configured[i] + "\n")
        f.write('\n')
        f.write('Current routes\n')
        for i in current_routes:
            f.write(i + "\n")

def checkGateway():
    logging.debug('Checking gateway')
    gf = '/etc/sysconfig/network'
    gws = {}
    result = False
    if os.path.isfile(gf):
        logging.debug(gf)
        with open(gf, 'r') as f:
            data = f.readlines()
            for l in data:
                if re.search(r'GATEWAY', l):
                    gw = re.search(r'GATEWAY=(.*)', l)
                    if gw.group(1):
                        gws['file'] = gw.group(1)
    rlst = ["route", "-n"]
    routes = live_routes(rlst)
    logging.debug(routes)
    for r in routes.splitlines():
        if re.match(r'0.0.0.0', r):
            rgw = re.match(r'0.0.0.0\s+(.*)\s+0.0.0.0', r)
            if rgw:
                gws['running'] = rgw.group(1).rstrip()
    if 'file' in gws and 'running' in gws:
        logging.debug('File configured %s.' % gws['file'])
        logging.debug('Running config %s.' % gws['running'])
        if gws['file'] == gws['running']:
            result = True 
    return result

def gen_output():
    logging.debug('Configured routes')
    lst = ["route", "-n"]
    lst1 = ["ip", "route", "show"]
    logging.debug('Routes currently live')
    current_routes = []
    ints = []
    for i in lst,lst1:
        routes = live_routes(i)
        logging.debug(routes)
        current_routes.append(routes)
        ints = valid_ints(routes)
    int_routes_configured = {}
    logging.debug(ints)
    for interface in ints:
        configured_routes = check_routes_exist(interface)
        logging.debug(configured_routes)
        int_routes_configured[interface] = configured_routes
    logging.debug(int_routes_configured)
    return ints,int_routes_configured,current_routes

if __name__ == "__main__":
    useage = """
    Validate the current routes and gateway of a host
    
    Store the current routes running on the host to a file
    %prog [-f filename] [-v]
    
    Validate the running gateway and the configured gateway match
    %prog [-g] [-v]
    """
    parser = OptionParser(useage)
    parser.add_option("-f", dest="filename", action="store", help="filename to save data to")
    parser.add_option("-g",dest="gateway", action="store_true", help="check gateways match")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity") # will set to False later
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    if options.filename:
        logging.debug(options.filename)
        ints,int_routes_configured,current_routes = gen_output()
        save_output(ints,int_routes_configured,current_routes,options.filename)
        logging.debug(ints,int_routes_configured,current_routes)
#        save_output(details,options.filename)
    elif options.gateway:
        logging.debug('Validating gateway')
        result = checkGateway()
        logging.debug(result)
        if result == False:
            print('Configured gateway and running gateway do not match')
            sys.exit(1)
    else:
        details = gen_output()
        print(details)
        logging.debug(details)
