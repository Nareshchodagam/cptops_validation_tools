#! /usr/bin/python

import os
import sys,traceback
from optparse import OptionParser
import subprocess
import logging
import cmd
import re
import shlex

#TODONB: have some way of ensuring it checks entry assumptions so it doesn't fix the host in an unknown state on rebooting

#supported commands
START = 'Start'
STOP = 'Stop'
TEST='test'

SCRIPT_LIST=[]


BIG_STOP_GACKP_SCRIPT="""

# Removing crontab for traffic
crontab -r
cronRC=$?
sleep 2
#Killing gack_parser and gack_mailbox_monitor scripts'
pkill -f "perl ./gack_" #Stops gack_parser.pl and gack_mailbox_monitor.pl
pkillRC=$?

if [ cronRC -ne 0 ] || [ $pkillRC -ne 0 ]
then
  exit 1
else
  exit 0
fi


"""

COMMAND_SETS = {
         #GENERIC COMMANDS
	'EXIT_1' : 'exit 1',
        'VERBOSE_ON' : 'set -x\n',
        'VERBOSE_OFF' : 'set +x\n',
        'KILL_TOMCAT' : [ '([ $(ps -ef | grep Bootstrap | grep -v grep | wc -l) -eq 0 ] || ps -ef | grep Bootstrap | grep -v grep | awk \'{print $2}\' | xargs kill)'],
        'TEST_SFDC_USER' : [ '[ "\$USER" == "sfdc" ]' ],
        'TEST_JAVA_0' : ['[ $(ps -ef | grep java | grep -v grep | awk \"{print $2}\" | wc -l) -eq 0 ]' ],
        'TEST_JAVA_1' : ['[ $(ps -ef | grep java | grep -v grep | awk \"{print $2}\" | wc -l) -eq 1 ]' ],
        'TEST_JAVA_6' : ['[ $(ps -ef | grep java | grep -v grep | awk \"{print $2}\" | wc -l) -eq 6 ]' ],
        'KILL_JAVA' : [ '[ $(ps -ef | grep java | grep -v grep | wc -l) -eq 0 ] || (ps -ef | grep java | grep -v grep | awk \'{print \$2}\' | xargs kill || sleep 180)', 'TEST_JAVA_0' ], 
        'SLEEP_10' : ['sleep 10'],
        'SLEEP_60' : ['sleep 60'],

	#ARGUS commmands
        'SOURCE_TDSB' : ['TEST_SFDC_USER', 'shopt -s expand_aliases','source /home/sfdc/opentsdb-2.1.0/tsdb.rc','cd /home/sfdc/opentsdb-2.1.0' ],
        'SOURCE_ARGUS_RC' : [ 'TEST_SFDC_USER', 'shopt -s expand_aliases', 'source /home/sfdc/argus.rc' ],
        'START_AJNA_CHI' : [ '(startchicon)', 'SLEEP_10'],
        'START_SFZ_IMT' : [ '(startsfzimt)', 'SLEEP_60' ],
        'START_SFZ_AJNABUS' : [ '(startsfzajnabus)', 'SLEEP_10' ],
        'START_SFZ_LOGHUB' : [ '(startsfzloghub)', 'SLEEP_10' ],
        'START_WAS_LOGBUS' : [ '(startwaslogbus)', 'SLEEP_10' ],
        'START_AJNA_WAS' : [ '(startwascon)' ],


        'START_AJNA' : ['SOURCE_ARGUS_RC', 'cd /home/sfdc/argus/kafkaconsumer','START_AJNA_CHI','START_SFZ_IMT','START_SFZ_AJNABUS','START_SFZ_LOGHUB','START_WAS_LOGBUS','START_AJNA_WAS', 'TEST_JAVA_6'],
        'START_TOMCAT' : [ 'SOURCE_ARGUS_RC', 'starttomcat',],
        'START_METRICS' : [ 'SOURCE_ARGUS_RC', 'startcommitclient', 'TEST_JAVA_1' ],
        'START_ANNOTATION' : [ 'SOURCE_ARGUS_RC', 'startannotationclient', 'TEST_JAVA_1' ],
        'START_ALERT' : [ 'SOURCE_ARGUS_RC', 'startalertclient', 'TEST_JAVA_1'],
        'START_TDSBR' : ['SOURCE_TDSB','starttsdb' ],
        'START_TDSBW' : [ 'SOURCE_TDSB', 'startdsbwrite' ],


	#GACKPARSER
	'START_SENDMAIL' : ['service sendmail start'],
	'STOP_SENDMAIL' : ['service sendmail stop'],
	'STARTGACKPARSER' : ['crontab /var/traffic/cron_job'],
        'STOP_GACKP' : [ BIG_STOP_GACKP_SCRIPT ],
        'START_GACKP' : [ 'STARTGACKPARSER' ],
          


	#DELPHI


        'CD_DELPHI' : [ 'cd /home/delphi/current/dust-delphi/delphi/build' ],  
        'CHECK_DELPHI_COUNT' : ['ps -ef | grep -i "[d]elphi.app.properties" | wc -l > delphicount' ],
        'ANT_STOP_DELPHI' : [ 'if grep "^1\$" delphicount; then ./ant stop; fi' ],  
        'ANT_START_DELPHI' : [ 'if grep "^1\$" delphicount; then ./ant start; fi' ],  
        'STOP_DELPHI' : [ 'CD_DELPHI', 'CHECK_DELPHI_COUNT', 'ANT_STOP_DELPHI' ],
        'START_DELPHI' : [ 'CD_DELPHI', 'ANT_START_DELPHI' ]

	
	
}

SCRIPTS_BY_USER_HOSTTYPE = {

	#ARGUS 
	'^shared.*argusws.*' : [('sfdc', { STOP : ['KILL_TOMCAT'], START : ['START_TOMCAT'] })],
	'^shared.*argusui.*' : [('sfdc', { STOP : ['KILL_TOMCAT'], START : ['START_TOMCAT'] })], 
	'^shared.*argusajna.*' : [('sfdc', { STOP : ['KILL_JAVA'], START : ['START_AJNA'] })], 
	'^shared.*argusmetrics.*' : [('sfdc', { STOP : ['KILL_JAVA'], START : ['START_METRICS'] })], 
	'^shared.*argusannotation.*' : [('sfdc', { STOP : ['KILL_JAVA'], START : ['START_ANNOTATION'] })], 
	'^shared.*argusalert.*' : [('sfdc', { STOP : ['KILL_JAVA'], START : ['START_ALERT'] })], 
	'^shared.*argustsdbr.*' : [('sfdc', { STOP : ['KILL_JAVA'], START : ['START_TDSBR'] })], 
	'^shared.*argustsdbw.*' : [('sfdc', { STOP : ['KILL_JAVA'], START : ['START_TDSBW'] })],
        '^testcommand' : [('dsheehan', { TEST: ['TEST_JAVA_1']})],

	#GACKPARSER
	'(^dust-app2.*sfm)|(^dust-app2.*sfz)' : [('traffic', { STOP : ['STOP_GACKP'], START : ['START_GACKP'] }),
						 ('root', { STOP : ['STOP_SENDMAIL'], START : ['START_SENDMAIL'] })],
	
	#DELPHI
	'(^dust-app1.*sfm)|(^dust-app1.*sfz)' : [('delphi', { STOP : ['STOP_DELPHI'], START : ['START_DELPHI'] })],



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

def get_local_hostname():
        if options.test_host:
	  	return options.test_host
	else:
        	return  os.popen("hostname -s").readlines()[0].rstrip('\n')

def get_commandlist_from_hostname():
        myhostname = get_local_hostname()
        logging.debug( myhostname )
        script=()
        for key in SCRIPTS_BY_USER_HOSTTYPE:
                if re.match(key,myhostname):
                        script = SCRIPTS_BY_USER_HOSTTYPE[key]
                        break;
        if not script:
                print 'host type not found'
        else:
		print 'Host matching : ' + myhostname +  ' matched: ' + key

        return script

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

def process_ant_commands(commandstr,message):
        mylist = get_commandlist_from_hostname()
        logging.debug( mylist )
        if mylist:
           return manage_ant_services(mylist, commandstr,message)
        else:
           return {}

def stop_ant_services():
        return process_ant_commands('su - {0}  -c "cd {1}; build/ant stop"', "Starting ant apps .....")

def start_ant_services():
        return process_ant_commands('su - {0}  -c "cd {1}; build/ant start"', "Stopping ant apps .....")

def test_ant_services():
        return process_ant_commands('su - {0}  -c "cd {1}; pwd; ls -al build/ant; ps -fu {0} | grep {1}"', "checking service for user : ")

def start_services():
        print 'processing commands top start applications'
        return process_commands([START])

def stop_services():
        print 'processing commands to stop applications'
        return process_commands([STOP])

def display_services():
        return process_commands([START,STOP,TEST])

def test_commands():
        print 'processing commands to stop applications'
        return process_commands([TEST])

def get_command_set(cmd):
  result = [] 
  for command in COMMAND_SETS[cmd]:
    if command in COMMAND_SETS.keys():
      result.extend(get_command_set(command))
    else:
      result.append(command + ' || ' + COMMAND_SETS['EXIT_1'] + '\n')
  return result   
		 
def gen_command(commands):
        result = []
        logging.debug( 'gen_command: ' + str(commands) )
        for command in commands: 
	  result.extend( get_command_set(command) )
          logging.debug( 'gen_command results: ' + str(result) )
        return [COMMAND_SETS['VERBOSE_ON']] + result
	
def process_commands(tasks):
      for task in tasks:
        assert task in (STOP,START,TEST), 'unrecocnised task specified'
      results = {}
      for task in tasks:    
        payloadlist = []
        logging.debug( SCRIPT_LIST )
        
        if SCRIPT_LIST:
          for script in SCRIPT_LIST:
	    user, mycommand = script
            logging.debug( mycommand )
            if not task in mycommand.keys():
		continue
	    mycmdlist= gen_command(mycommand[task])
            payload = 'su - ' + user + ' -c "' + ''.join(mycmdlist) + '"'
            if options.displayonly:
                payloadlist.append(payload)
		results[task]=payloadlist
	    else:    
                results[payload] = run_cmd_line(['/bin/bash', '-c',  payload])
       
      return results          

def process_results(results):
	"""
	derives cumulative return value for all results of command executed to return to shell
	"""       
        # set to 1 first in case there are no results 
        ret_val = 1 if len(results.keys())==0 else 0
        logging.debug( results )
        for key in results:
                print 'Command Executed: ' + key
                print 'Command Output: ' + results[key]['output']
                ind_val = results[key]['returncode']
                ret_val = ret_val + ind_val #simply adding the numeric return codes gives us the cumulative value
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
    parser.add_option("--start_ant", dest="start_ant_service", action="store_true", help="The kernel version host should have")
    parser.add_option("--stop_ant", dest="stop_ant_service", action="store_true", help="The RH release host should have")
    parser.add_option("--test_ant", dest="test_all_functions", action="store_true")
    parser.add_option("--start", dest="start_service", action="store_true", help="start stuff")
    parser.add_option("--stop", dest="stop_service", action="store_true", help="stop stuff")
    parser.add_option("--testcommands", dest="testcommands", action="store_true", help="stop stuff")
    parser.add_option("--test_host", dest="test_host", help="test stuff")
    parser.add_option("--displayonly", dest="displayonly", action="store_true", help="display stuff")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="Verbosity")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    SCRIPT_LIST = get_commandlist_from_hostname()
    if options.test_all_functions:
        result = test_services()
        exit(process_results(result))
    elif options.start_ant_service:
        result = start_ant_services()
        exit(process_results(result))
    elif options.stop_ant_service:
        result = start_ant_services()
        exit(process_results(result))
    elif options.testcommands:
	result = test_commands()
        sys.exit(process_results(result))
    elif options.start_service:
	result = start_services()
        sys.exit(process_results(result))
    elif options.stop_service:
	result = stop_services()
        sys.exit(process_results(result))
    elif options.displayonly:
	results = display_services()
        for key in results:
          print '====================== Command : '  + key
          print 'Script :' 
          print '-----------------------------------------'
          for line in results[key]:
		print line
    else:
        print(usage)

