#!/usr/bin/python
"""Code to check endpoints for proxy hosts"""

import os
import re
import sys
import socket
import subprocess
import logging
from optparse import OptionParser
import subprocess
import urllib2
import urllib
from urllib2 import URLError

#wget --header "X-Salesforce-Forwarded-To: v_CLUSTER.salesforce.com" --header "X-Salesforce-SIP: 10.13.37.1"
#--header "Host: www.test.com" -O - http://`hostname -f`:8084/smth.jsp



def set_end_point(inst):
    """
    This funciton is used to get the endpoint. This is different for SFM/CRD.
    :param inst: instance/POD name
    :return end_point: end_point
    """
    if 'sfm' in socket.gethostname().split('-')[3].split('.')[0]:
        end_point = 'mobile1.t.salesforce.com'
    elif 'crd' in socket.gethostname().split('-')[3].split('.')[0]:
        end_point = 'na2-blitz01.soma.salesforce.com'
    else:
        end_point = '{0}.salesforce.com' .format(inst)
    return end_point


def testEndPoint(inst, tcp_port, end_point=False):
    if end_point:
       end_point = end_point
    else:
       end_point = set_end_point(inst)
    headers = {'X-Salesforce-Forwarded-To': end_point,
               'X-Salesforce-SIP': '10.13.37.1',
               'Host': 'www.test.com'
               }
    url = 'http://' + hostname + ':' + tcp_port + '/smth.jsp'
    request = urllib2.Request(url, None, headers)

    try:
        response = urllib2.urlopen(request)
        r_output = response.read()
        logging.debug(response.headers)
        logging.debug(r_output)
        logging.debug(response.code)
        return response.headers,r_output,response.code, end_point
    except URLError, e:
        if 'crd' in socket.gethostname().split('-')[3].split('.')[0]:
            return testEndPoint(inst, tcp_port, 'na2-blitz02.soma.salesforce.com')
        else:
            print('Failed to open %s : %s' % (url, e))
            sys.exit(1)


def parseResponse(r_output,inst,tcp_port, end_point):
    data = { 'H': 'www.test.com', 'APPSERVINST': inst, 'port': tcp_port, 'IP': '10.13.37.1'}
    results = {'H': False, 'INST': False, 'APPSERVINST': False, 'port': False,
               'IP': False, 'SIP': False }
    for l in r_output.splitlines():
        SIP = 'X-Salesforce-SIP : ' + data['IP']
        H = 'Host : ' + data['H']
        RIP = 'Request IP : ' + data['IP']
        if inst == 'ap0':
            AppServ = 'DefaultAppServerPath: http://ap.salesforce.com'
        elif inst == 'eu0':
            AppServ = 'DefaultAppServerPath: http://emea.salesforce.com'
        elif inst == 'na0':
            AppServ = 'DefaultAppServerPath: http://ssl.salesforce.com'
        else:
            AppServ = 'DefaultAppServerPath: http://' + end_point
        XForward = 'X-Salesforce-Forwarded-To : ' + end_point
        if 'crd' in socket.gethostname().split('-')[3].split('.')[0]:
            Port = 'eng.sfdc.net:' + data['port']
        else:
            Port = 'ops.sfdc.net:' + data['port']
        if re.search(SIP, l):
            results['SIP'] = True
        if re.search(H, l):
            results['H'] = True
        if re.search(RIP, l):
            results['IP'] = True
        if re.search(AppServ, l):
            results['APPSERVINST'] = True
        if re.search(XForward, l):
            results['INST'] = True
        if re.search(Port, l):
            results['port'] = True
    return results

def parseResults(results,inst,p):
    logging.debug(results)
    if False in results.values():
        print('Error with testing the end point correctly on %s port %s' % (inst,p))
        sys.exit(1)
    else:
        print('Tested endpoint successfully on %s port %s' % (inst,p))


def get_inst(hostname):
    m = re.search(r'((.*).ops.sfdc.net|(.*).eng.sfdc.net)', hostname)
    if m:
        short_host = m.group(1)
        lst = short_host.split("-")
    return lst

def get_hostname():
    hostname = socket.gethostname()
    return hostname

if __name__ == "__main__":
    usage = """
    Use to validate the proxy on a certain port is working as expected

    %prog [-p number]

    %prog -p 8084
    """
    parser = OptionParser(usage)
    parser.add_option("-p", action="store", dest="port", help="Port to check")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity") # will set to False later
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    hostname = get_hostname()
    short_host = hostname.replace('.ops.sfdc.net', '')
    inst,hfunc,node,site = get_inst(hostname)
    if options.port:
        tcp_ports = [options.port]
    else:
        tcp_ports = ['8084', '8085']
    if re.match(r'sr', inst):
        print('Standard test does not work ')
    else:
        for p in tcp_ports:
            r_headers,r_output,r_code, end_point = testEndPoint(inst, p)
            results = parseResponse(r_output,inst,p, end_point)
            parseResults(results,inst,p)
