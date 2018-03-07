#!/usr/bin/env python

# imports
from argparse import ArgumentParser
import json
from datetime import datetime
from os import environ, chmod
import logging

CPTFILE = '/etc/cptrelease'
SFDCFILE = '/etc/sfdc-release'


def read_jsonfile(filename):
    try:
        with open(filename) as f:
            f_read = f.read()
            return json.loads(f_read)
    except (IOError, ValueError) as e:
        logger.warning(e)
        return {}


def check_sudouser():
    if environ['USER'] != "root":
        logger.error("Sadly you need to run me as root")
        exit(1)


def custom_logger():
    """
    This function is used to set custom logger.
    :return:
    """
    # Setting up custom logging
    c_logger = logging.getLogger('write_cptrelease.py')

    c_logger.setLevel(logging.DEBUG if args.verbose is True else logging.INFO)

    # create a Stream handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if args.verbose is True else logging.INFO)

    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)

    # add the handlers to the logger
    if not c_logger.handlers:
        c_logger.addHandler(ch)
    c_logger.propagate = False

    return c_logger


if __name__ == "__main__":
    parser = ArgumentParser(prog='write_cptrelease.py', usage='\n%(prog)s --last \n%(prog)s -b 2018.01 -c 012345 ')
    parser.add_argument("--last", "-l", dest="lastbundle", action="store_true", default=False,
                        help="To get last patch Bundle")
    parser.add_argument("-b", dest="bundle", help="Bundle Version")
    parser.add_argument("-c", dest="casenumber", help="Case Number")
    parser.add_argument("--verbose", "-v", action="store_true", dest="verbose", default=False, help="verbosity")

    args = parser.parse_args()
    logger = custom_logger()

    check_sudouser()

    json_data = read_jsonfile(CPTFILE)

    if args.lastbundle:
        try:
            with open(SFDCFILE) as f:
                f_content = f.readlines()
            last_bundle = ".".join(f_content[0].split()[1].split('-')[2:])  # Hack to get last installed OS bundle
            json_data['lastPatchBundle'] = last_bundle
        except IOError as e:
            logger.warning("Can not open file %s", e)
            json_data['lastPatchBundle'] = ""

        json_data['patchingStartTime'] = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
        json_data['patchingOwner'] = environ['SUDO_USER']

    if args.bundle and args.casenumber:
        json_data['currentPatchBundle'] = args.bundle
        json_data['patchingEndTime'] = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
        json_data['caseNumber'] = args.casenumber

    try:
        with open(CPTFILE, 'w') as f:
            json.dump(json_data, f)
    except IOError as e:
        logger.error(e)

    chmod(CPTFILE, 0644)
