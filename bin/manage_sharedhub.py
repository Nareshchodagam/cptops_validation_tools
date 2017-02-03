#!/usr/bin/python

import os
import sys,traceback
from optparse import OptionParser
import subprocess
import logging
import cmd


def run_cmd_line(cmdline):

        result = {}
        result['returncode'] = 1
        result['output']= ''
        ouptut = ''
        #try:
        run_cmd = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = run_cmd.communicate()
        result['returncode'] = run_cmd.returncode
        result['output'] = out if out else ''
        result['output'] = result['output'] + '\n' + err if err else result['output']
        #except OSError as e:
        #    result['output'] = e.message

        logging.debug( 'run_cmd_line result : ' +str(result) )
        return result




def get_running_list(filename,cmd="ps -ef | grep hub_ | grep -v grep | grep -v root | awk '{print $1}' | sort | uniq"):
        filename='hubs.txt'
        try:
                os.remove(filename)
        except OSError:
                pass

        psout=os.popen(cmd).read()
        logging.debug( 'returned ', str(len(psout)), ' lines' )
        #if len(psout)==0:
        #    raise Exception("No users found to process")
        outfile=open(filename,'w')
        outfile.write(psout)
        outfile.close

def manage_ant_services(filename,cmd,message):
        full_result={}
        with open(filename) as f:
                lines=f.read().splitlines()
        logging.debug( 'Lines:' + str(lines) )
        logging.debug( cmd )
        for line in lines:
                cmd_line = cmd % (line)
                logging.debug( cmd_line )
                toexecute = [statement for statement in cmd_line.split('"')]
                param = toexecute[0].split() + toexecute[1:]
                print message + cmd_line
                result = run_cmd_line(param[:-1] )
                full_result[cmd_line] = result
        logging.debug ( full_result )
        return full_result

def stop_services(filename):
        get_running_list(filename)
        results = manage_ant_services(filename, 'su - %s -c "cd current/mandm-hub/hub/build/; ./ant stop"', "Stopping service .... " )
        return process_results(results)


def start_services(filename):
        results = manage_ant_services(filename,'su - %s -c "cd current/mandm-hub/hub/build/; ./ant start"', "Starting service .... ")
        return process_results(results)

def test_all(filename):
        get_running_list(filename)
        return manage_ant_services(filename, 'su - %s -c "ls -alrt"', "checking service for user : ")


def save_lhub_fs(filename):
        filename='hubs.txt'
        try:
                os.remove(filename)
        except OSError:
                pass

        psout=os.popen("ps -ef | grep hub_ | grep -v grep | grep -v root | awk '{print $1}' | sort | uniq").read()
        outfile=open(filename,'w')
        outfile.write(psout)
        outfile.close

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

    Stop running pod level hub services
    %prog -k

    Start pod level hub services
    %prog -s

    """
    parser = OptionParser(usage)
    parser.add_option("-s", dest="start_ant_service", action="store_true", help="The kernel version host should have")
    parser.add_option("-k", dest="stop_ant_service", action="store_true", help="The RH release host should have")
    parser.add_option("-t", dest="test_all_functions", action="store_true")
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="Verbosity")
    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    filename='hubs.txt'

    if options.test_all_functions:
        result = test_all(filename)
        logging.debug ( result )
        exit(process_results(result))
    elif options.start_ant_service:
        exit(start_services(filename))
    elif options.stop_ant_service:
        get_running_list(filename)
        exit(stop_services(filename))
    else:
        print(usage)


	
