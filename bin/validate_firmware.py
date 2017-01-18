#!/usr/bin/env python
from __future__ import print_function

# imports
import subprocess
import os
import shlex
import sys
import logging
import time
from subprocess import PIPE, Popen
from argparse import ArgumentParser, RawTextHelpFormatter


def validate_commands(command):
    """
    This function is test if the phaser related commands are present on host
    :param: command: The command to verify on localhost
    :return: True OR False
    """
    try:
        os.path.exists('/usr/bin' + command)
        return True
    except Exception as e:
        print("Command not found '{0}'".format(command))
        return False


def run_cmd(cmd):
    """
    This function will execute command on host and will return output and exit_status
    :param: cmd: Command to execute on host
    :return" output and return code
    """
    try:
        process_exec = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
        out, err = process_exec.communicate()
        logging.debug(out)
        print(err)
        exit_code = process_exec.wait()
        return out, exit_code
    except Exception as e:
        print("ERROR: Can't execute command '{0}'".format(e))
        sys.exit(0)


def validate_firmware():
    """

    :return:
    """
    cmd = '/usr/bin/tricorder -c'
    output, exit_code = run_cmd(cmd)
    if exit_code != 0:
        print("INFO: Firmware is not running on the latest")
        return output, True
    elif exit_code == 0:
        print("INFO: Firmware already updated, so quitting")
        sys.exit(0)


def execute_firmware():
    """
    This function is used to apply the latest firmware on host.
    :return: None
    """
    cmds = ['/usr/bin/communicator -f -v stable', '/usr/bin/phaser -m kill -v stable -d']
    for cmd in cmds:
        out, exit_code = run_cmd(cmd)
        if exit_code == 0:
            print("INFO: Successfully executed command '{0}'".format(cmd))
        else:
            print("ERROR: Something wrong with command '{0}'" .format(cmd))


# main
if __name__ == "__main__":
    parser = ArgumentParser(description="""This code is to check if the latest firmware applied or not """,
                            usage='%(prog)s [options]', formatter_class=RawTextHelpFormatter)
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    parser.add_argument("-t", dest='time_taken', action='store_true', default=True, help="Time taken by firmware process")
    parser.add_argument("-u", dest='update', action='store_true', default=False, help="To update firmware(Before Reboot)")
    parser.add_argument("-c", dest='check', action='store_true', default=False, help="To verify firmware(After Reboot)")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if args.update:
        start_time = time.time()
        cmds = ['tricorder', 'phaser', 'communicator']
        print("INFO: Checking if commands related to phaser have installed")
        tricorder, phaser, communicator = [validate_commands(cmd) for cmd in cmds]
        if tricorder and phaser and communicator:
            print("INFO: Phaser related commands are present on host")
            print("INFO: Validating, if firmware required an update")
            out, exit_status = validate_firmware()
            logging.debug(out)
            if exit_status:
                execute_firmware()
                if args.time_taken:
                    print("--- %s seconds ---" % (time.time() - start_time))
        else:
            print("ERROR: command not found 'tricorder - {0}', phaser - {1}, communicator - {2}".format(tricorder, phaser, communicator))

    elif args.check:
        print("INFO: Validating firmware...")
        output, exit_status = validate_firmware()
        if exit_status:
            print("INFO: Firmware was not updated to latest")
            sys.exit(1)


