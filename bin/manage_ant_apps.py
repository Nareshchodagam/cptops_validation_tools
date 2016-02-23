#! /usr/bin/python

import os
import sys,traceback
from optparse import OptionParser
import subprocess
import logging
import cmd
import re

ANT_DETAILS_BY_HOSTTYPE = {

        '^cfgdev-cidb.*' : [
                ('dca4', '/home/dca4/cheetah/cms/cidb/main' )

                ],

        '^cfgdev-cfgapp*' : [
                ('dca4', '/home/dca4/current/cidb/cidb' ),
                ('dca3', '/home/dca3/current/deployment/deployment-api' ),
                ('dca', '/home/dca/current/inventorydb/inventorydb' )

                ],

        '^cfgdev-cfgmaster*' : [
                ( 'dca' ,  '/home/dca/cheetah/cms/idbui/main'),
                ( 'dca2' , '/home/dca2/current/brownfield/brownfield'),
                ( 'dca3' , '/home/dca3/current/deployment/deployment-api' ),
                ( 'dca4' , '/home/dca4/current/cidb/cidb/build' )
                ],

        '^cfgdev-ftest*' : [
                ( 'sfdc', '/home/sfdc/cheetah/cms/inventory/main' ),
                ( 'sfdc' , '/home/sfdc/cheetah/cms/deployment/main'),
                ('sfdc' , '/home/sfdc/cheetah/cms/cidb/main' )
                ]
}

COMMAND_SETS = {
	'EXIT_1' : 'exit 1',
        'VERBOSE_ON' : [ 'set -e' ],
        'VERBOSE_OFF' : [ 'set +e' ],
        'KILL_TOMCAT' : [ 'ps -ef | grep Bootstrap | grep -v grep | awk "{print $2}" | xargs kill'],
        'SOURCE_TDSB' : ['TEST_SFDC_USER', 'shopt -s expand_aliases','source /home/sfdc/opentsdb-2.1.0/tsdb.rc','cd /home/sfdc/opentsdb-2.1.0'],
        'SOURCE_ARGUS_RC' : [ 'TEST_SFDC_USER', 'shopt -s expand_aliases', 'source /home/sfdc/argus.rc', 'cd /home/sfdc/argus/kafkaconsumer' ],
        'TEST_SFDC_USER' : [ '[ "$USER" == "sfdc" ]' ],
        'TEST_JAVA_1' : []
        'TEST_JAVA_6' : []
        'KILL_JAVA', : [ 'ps -ef | grep java | grep -v grep | awk "{print $2}" | xargs kill' ],


        'START_AJNA_CHI' : [ 'SOURCE_ARGUS_RC', 'startchicon'],
        'START_SFZ_IMT' : [ 'SOURCE_ARGUS_RC', 'startsfzimt' ],
        'START_SFZ_AJNABUS' : [ 'SOURCE_ARGUS_RC', 'startsfzajnabus'],
        'START_SFZ_LOGHUB' : [ 'SOURCE_ARGUS_RC', 'startsfzloghub' ],
        'START_WAS_LOGBUS' : [ 'SOURCE_ARGUS_RC', 'startwaslogbus' ],
        'START_AJNA_WAS' : [ 'SOURCE_ARGUS_RC', 'startwascon' ],
        'START_AJNA' : []


        'START_TOMCAT' : [ 'SOURCE_ARGUS_RC', 'starttomcat'],
        'START_METRICS' : [ 'SOURCE_ARGUS_RC', 'startcommitclient' ],
        'START_ANNOTATION' : [ 'SOURCE_ARGUS_RC', 'startannotationclient' ],
        'START_ALERT' : [ 'SOURCE_ARGUS_RC', 'startalertclient'],
        'START_TDSBR' : ['SOURCE_TDSB','starttsdb']
        'START_TDSWB' : [ 'SOURCE_TDSB', 'startdsbwrite' ]
}

SCRIPT_BY_HOSTTYPE = { 
'shared.*argusws.*' : ('sfdc', { 'start' : ['KILL_TOMCAT'], 'start' : ['START_TOMCAT'] }),
'shared.*argusui.*' : ('sfdc', { 'start' : ['KILL_TOMCAT'], 'start' : ['START_TOMCAT'] }), 
'shared.*argusajna.*' : ('sfdc', { 'start' : ['KILL_TOMCAT'], 'start' : ['START_TOMCAT'] }), 
'shared.*argusmetrics.*' : ('sfdc', { 'start' : ['KILL_TOMCAT'], 'start' : ['START_TOMCAT'] }), 
'shared.*argusannotation.*' : ('sfdc', { 'start' : ['KILL_TOMCAT'], 'start' : ['START_TOMCAT'] }), 
'shared.*argusalert.*' : ('sfdc', { 'start' : ['KILL_TOMCAT'], 'start' : ['START_TOMCAT'] }), 
'shared.*argustsdbr.*' : ('sfdc', { 'start' : ['KILL_TOMCAT'], 'start' : ['START_TOMCAT'] }), 
'shared.*argustsdbw1.*' : ('sfdc', { 'start' : ['KILL_TOMCAT'], 'start' : ['START_TOMCAT'] })



}

def get_local_hostname():
        return  os.popen("hostname -s").readlines()[0].rstrip('\n')

def get_commandlist_from_hostname():
        hostname = get_local_hostname()
        ant_details_list = []
        for key in ANT_DETAILS_BY_HOSTTYPE:
                print key, hostname
                if re.match(key,hostname):
                        ant_details_list = ANT_DETAILS_BY_HOSTTYPE[key]
                        break;
        if not ant_details_list:
                print 'host type not found'

        return ant_details_list

def run_cmd_line(cmdline):

        result = {}
        result['returncode'] = 1
        result['output']= ''
        ouptut = ''
        run_cmd = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = run_cmd.communicate()
        result['returncode'] = run_cmd.returncode
        result['output'] = out if out else ''
        result['output'] = result['output'] + '\n' + err if err else result['output']

        logging.debug( 'run_cmd_line result : ' +str(result) )
        return result



def manage_ant_services(ant_details_list,cmd,message):
        full_result={}
        logging.debug( cmd )
        for ant_details in ant_details_list:
                cmd_line = cmd.format(*ant_details)
                logging.debug( cmd_line )
                toexecute = [statement for statement in cmd_line.split('"')]
                param = toexecute[0].split() + toexecute[1:]
                print message + cmd_line
                result = run_cmd_line(param[:-1] )
                full_result[cmd_line] = result
        logging.debug ( full_result )
        return full_result

def process_commands(commandstr,message):
        mylist = get_commandlist_from_hostname()
        logging.debug( mylist )
        if mylist:
           return manage_ant_services(mylist, commandstr,message)
        else:
           return {}

def stop_services():
        return process_commands('su - {0}  -c "cd {1}; build/ant stop"', "Starting ant apps .....")


def start_services():
        return process_commands('su - {0}  -c "cd {1}; build/ant start"', "Stopping ant apps .....")

def test_services():
        return process_commands('su - {0}  -c "cd {1}; pwd; ls -al build/ant; ps -fu {0} | grep {1}"', "checking service for user : ")


def process_results(results):
        ret_val = 1 if len(results.keys())==0 else 0
        logging.debug( results )
        for key in results:
                print 'Command: ' + key
                print 'Command Output: ' + results[key]['output']
                ind_val = results[key]['returncode']
                ret_val = ret_val + ind_val if ind_val !=0 else 0
                print 'Command ReturnCode: ' + str(ind_val)
        return ret_val

if __name__ == "__main__":
    usage = """

    This script stops and starts hub processes for currently running pods.

    Stop running ant applications
    %prog --stop

    Start ant applications
    %prog --start

    Test ant applications
    %prog --test

    """
    parser = OptionParser(usage)
    parser.add_option("--start", dest="start_ant_service", action="store_true", help="The kernel version host should have")
    parser.add_option("--stop", dest="stop_ant_service", action="store_true", help="The RH release host should have")
    parser.add_option("--test", dest="test_all_functions", action="store_true")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="Verbosity")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if options.test_all_functions:
        result = test_services()
        exit(process_results(result))
    elif options.start_ant_service:
        result = start_services()
        exit(process_results(result))
    elif options.stop_ant_service:
        result = start_services()
        exit(process_results(result))
    else:
        print(usage)


