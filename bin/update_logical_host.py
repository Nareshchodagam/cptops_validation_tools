#!/usr/bin/env python
'''
        Script for updating logical host connectors in GUS cases
'''
from base import Auth
from base import Gus
from common import Common 
from optparse import OptionParser
import base64
import logging
import ConfigParser
import getpass
import re
import json
import sys
from datetime import datetime, date, time, timedelta
import pprint

config = ConfigParser.ConfigParser()
config.readfp(open('creds.config'))

#Dummy Commit

def updateLogicalConnectors(Id, Dict, session):
    
    gusObj = Gus()
    updates = gusObj.updateLogicalConnector(Id, Dict, session)
    logging.debug(updates)
    return updates

def createLogicalHostsDict(ecode, emessage):
    data = {
            'Exit_Code__c': ecode,
            'Exit_Message__c': emessage
            }
    return data

def getLogicalConnetorDetails(caseId,session):
    gusObj = Gus()
    logical_host_ids = []
    query = "select Id,Logical_Host__c,Case_Record__c from SM_Case_to_LogicalHost_Connector__c where Case_Record__c='" + caseId +"'"
    case_details = gusObj.run_query(query,session)
    #pp.pprint(case_details)
    if case_details['records']:
        for r in case_details['records']:
            #logical_host_ids.append(r['Id'])
            return case_details['records']

def getLogicalConnectors(hosts, session):
    gusObj = Gus()
    #object = 'Tech_Asset_Discovery__c'
    objecta = 'SM_Logical_Host__c'
    os_details = {} 
    for h in hosts:   
        logging.debug(h)
        if h != None:
            query = "Select Id, Host_Name__c from " + objecta + " \
            where Host_Name__c='" + h + "'" 
            details = gusObj.run_query(query, session)
            if 'records' in details and details['totalSize'] != 0:
                os_details[h] = details['records'][0]['Id']

    return os_details

def getCaseId(caseNum,session):
    gusObj = Gus()
    case_details = gusObj.get_case_details_caseNum(caseNum,session)
    return case_details.rstrip()

if __name__ == '__main__':
    
    usage = """
    
    
    """
    parser = OptionParser(usage)
    parser.add_option("-c", "--case", dest="caseNum",
                            help="The caseId of the case to attach the file ")
    parser.add_option("-e", "--exitcode", dest="exitcode",
                            help="The exit code to apply  ")
    parser.add_option("-m", "--exitmassage", dest="exitmessage",
                            help="The message to update with ")
    parser.add_option("-H", dest="hostlist", action="store", help="The target hostname(s)")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="verbosity") # will set to False later
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    # set username and details of case

    try:
        gpass = config.get('GUS', 'guspassword')
    except ConfigParser.NoOptionError,e:
        gpass = getpass.getpass("Please enter your GUS password: ")
    username = config.get('GUS', 'username')
    # instantiate auth object and generate session dict
    authObj = Auth(username,gpass)
    session = authObj.login()
    pp = pprint.PrettyPrinter(indent=4)
    if options.caseNum:
        caseId = getCaseId(options.caseNum,session)
        logical_host_records = getLogicalConnetorDetails(caseId,session)
        #pp.pprint(logical_host_records)
        hosts = options.hostlist.split(',')    
        logical_hosts = getLogicalConnectors(hosts, session)
        #pp.pprint(logical_hosts)
        #logical_host_ids = getLogicalConnectors(hosts, session)
        #print(logical_host_ids)
        for r in logical_host_records:
            for h in logical_hosts:
                if logical_hosts[h] == r['Logical_Host__c']:
                    logging.debug('%s %s' % (r['Id'],r['Logical_Host__c']))
                    dict = createLogicalHostsDict(options.exitcode, options.exitmessage)
                    details = updateLogicalConnectors(r['Id'], dict, session)
                    logging.debug(details)
        #for h in logical_hosts:
        #    print(logical_host_records[h])
        #    dict = createLogicalHostsDict(logical_host_ids[h],caseId, options.exitcode, options.exitmessage)
        #    print(dict)
            #details = updateLogicalConnectors(caseId, dict, session)
            #print(details)
        
    
