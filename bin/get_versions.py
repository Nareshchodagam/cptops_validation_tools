#/usr/bin/python

from optparse import OptionParser
import base64
import logging
import getpass
import re
import json
import sys
import os
from datetime import datetime, date, time, timedelta
import subprocess
import pprint

roledict={"app": ["lightcycle-snapshot","mandm-agent","sfdc-base","onboarding", "sfdc-splunk-forwarder", "caas"],
            "dapp": ["lightcycle-snapshot","mandm-agent","sfdc-base","onboarding", "sfdc-splunk-forwarder"],
            "acs": ["lightcycle-snapshot","mandm-agent","sfdc-base", "sfdc-splunk-forwarder"],
            "cbatch": ["lightcycle-snapshot","mandm-agent","sfdc-base", "sfdc-splunk-forwarder"],
            "mq": ["mq-broker", "sfdc-splunk-forwarder"], "sitesproxy": ["sitesproxy", "sfdc-splunk-forwarder"] }

def getData(fname):
    with open(fname, 'r') as input_data:
        d = input_data.readlines()
        return d

def writeData(fname,data):
    with open(fname, 'w') as input_data:
        input_data.write(data)

def parseData(data):
    app_vers = {}
    for l in data:
        m = re.search(r'Current version.*: manifest - (.*.rmf)', l)
        if m:
            manifest = m.group(1)
            logging.debug(manifest)
            app,ver = manifest.split('__', 1)
            logging.debug("%s %s" % (app,ver))
            app_vers[app] = manifest
    return app_vers

def parseDatabyVer(data):
    installed_software = []
    app_line = re.compile(r'.*\((.*)\).*\s(.*.rmf$)')

    for l in data:
       m = app_line.search(l)
       if m:
        app_name = m.group(2)
        ver_name = m.group(1)
        ret_val = "{0}@{1}".format(app_name.split('_')[0], ver_name)
        installed_software.append(ret_val)
    _APPS = ','.join(installed_software)
    return _APPS

def genManifestData(apps,app_vers):
    app_lst = []
    for app in apps:
        if app in app_vers:
            app_lst.append(app_vers[app])
    m = "-manifests " + ",".join(app_lst) +"\n"  
    return m

if __name__ == '__main__':
    
    usage = """
    Script for generating manifest lines for RR    
    """
    parser = OptionParser(usage)
    parser.set_defaults(outputname='manifests.txt')
    parser.add_option("-a", "--applist", dest="applist", help="The app list to check")
    parser.add_option("-r", "--role", dest="role", help="Role to get list of apps")
    parser.add_option("-f", "--filename", dest="filename", help="Filename with version data to parse")
    parser.add_option("-o", "--outputname", dest="outputname", help="Filename to output manifest data")
    parser.add_option("-u", "--user", dest="user", default="sfdc", help="User apps are installed as")
    parser.add_option("--versions", action="store_true", dest="versions", default=False, help="Pull apps by versions")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity") # will set to False later
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    pp = pprint.PrettyPrinter(indent=4)
    app_vers = {}
    output_file = options.outputname
    
    if options.filename and options.role:
        logging.debug(options.filename)
        data = getData(options.filename)
        app_vers = parseData(data)
        logging.debug(app_vers)
        apps = roledict[options.role]
        logging.debug(apps)
        manifest_data = genManifestData(apps,app_vers)
        writeData(output_file,manifest_data)
        
    if options.filename and options.applist:
        logging.debug(options.filename)
        data = getData(options.filename)
        app_vers = parseData(data)
        logging.debug(app_vers)
        apps = options.applist.split(",")
        logging.debug(apps)
        manifest_data = genManifestData(apps,app_vers)
        writeData(output_file,manifest_data)
        
    if options.filename and options.versions:
        logging.debug(options.filename)
        data = getData(options.filename)
        app_vers = parseDatabyVer(data)
        logging.debug(app_vers)
        writeData(output_file, app_vers)
