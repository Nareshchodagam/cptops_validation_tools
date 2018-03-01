#!/usr/bin/python

import argparse
import os
import logging
import sys

# Insights-specific script to create and/or update /home/sfdc/patching.json file
# 
# Valid JSON content: { "patching" : true/false }
# 
# This script makes an attempt to change the mode of the file to 644 and the user
# and group owner to those of the parent dir /home/sfdc. It does not fail on
# chmod or chown failure since they are not critical; it does, however, report
# them.
# 
# Usage:
# insights_argus_monitor.py -a enable [-v]
# insights_argus_monitor.py -a disable [-v]

# getpwuid(stat(filename).st_uid).pw_name
# uid = pwd.getpwnam("nobody").pw_uid
# gid = grp.getgrnam("nogroup").gr_gid


DIR = "/home/sfdc/"
FILENAME = "patching.json"
PATH = DIR + FILENAME

def changeMode():
    try:
        os.chmod(PATH, 0644)
    except Exception as e:
        logging.warning('unable to change mode of '+PATH)
    else:
        logging.info('changed mode of '+PATH)

def changeOwner():
    try:
        uid = os.stat(DIR).st_uid
        gid = os.stat(DIR).st_gid
        os.chown(PATH, uid, gid)
    except Exception as e:
        logging.warning('unable to change the owner of '+PATH)
    else:
        logging.info('changed owner of '+PATH)

def genContent(action):
    return '{ "patching" : '+action+' }\n'

def processOptions():
    parser = argparse.ArgumentParser('Insights-specific script to create/update '+PATH+' file that controls argus monitoring for the host')
    parser.add_argument('-a', '--action', help='perform given action: enable/disable', required=True)
    parser.add_argument('-v', '--verbose', help='print debug info', dest='verbose', action='store_true', default=False)
    options = parser.parse_args()
    
    if options.action.lower() != 'enable' and options.action.lower() != 'disable':
        logging.error('action '+options.action+' not supported; use enable or disable')
        sys.exit(1)

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
    	logging.basicConfig(level=logging.INFO)

    return options

def main():
	# process command line arguments, perform some checks 
    options = processOptions()
    
    # generate the json file contents based on the passed argument
    if options.action.lower() == 'enable':
        content = genContent('false')
    else:
        content = genContent('true')
    logging.debug('content: '+content.strip())
    
    # make sure parent dir exists
    if not os.path.isdir(DIR):
        logging.error('directory '+DIR+' does not exist!')
        sys.exit(1)
    
    # write contents to the file
    try:
        f = open(PATH,'w+')
        f.write(content)
        f.close()
    except Exception as e:
        logging.error('unable to write to '+PATH)
        print(e)
        sys.exit(1)
    else:
        logging.info(content.strip()+' written to '+PATH)

    # TODO: add checks before calling these
    changeMode()
    changeOwner()


if __name__ == '__main__':
    status = main()
    sys.exit(status)
