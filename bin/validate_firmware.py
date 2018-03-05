#!/usr/bin/python
from __future__ import print_function

# imports
import sys
import logging
import time
import errno
from argparse import ArgumentParser, RawTextHelpFormatter
try:
    from tricorder import cli as tricorder
    from phaser import cli as phaser

    frb_install = True
except:
    frb_install = False

def validate_commands():
    """
    This function is test if the phaser related commands are present on host
    :param: command: The command to verify on localhost
    :return: True OR False
    """
    return frb_install


def validate_firmware(vintage):
    """

    :return:
    """
    exit_code = tricorder.check_platform_preferred(state='stable')
    if exit_code != 0:
        logging.warn("INFO: Firmware is not running on the latest")
        return True
    elif exit_code == 0:
        logging.info("INFO: Firmware already updated, so quitting")
        sys.exit(0)


def execute_firmware(vintage):
    """
    This function is used to apply the latest firmware on host.
    :return: None
    """
    retc = 0
    retc = phaser.fire(debug=True)# mode='stun',vintage='stable' is default
    if retc:
        logging.warn("ERROR: Something wrong with stun run '{0}'" .format(retc))
        return retc
    retc = phaser.fire(mode='kill', vintage=vintage, debug=True)
    if not retc:
        logging.info("INFO: Successfully executed firmware update via phaser")
    else:
        logging.warn("ERROR: Something wrong with phaser update run '{0}'" .format(retc))
    return retc


# main
if __name__ == "__main__":
    parser = ArgumentParser(description="""This code is to check if the latest firmware applied or not """,
                            usage='%(prog)s [options]', formatter_class=RawTextHelpFormatter)
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    parser.add_argument("-t", dest='time_taken', action='store_true', default=True, help="Time taken by firmware process")
    parser.add_argument("-u", dest='update', action='store_true', default=False, help="To update firmware(Before Reboot)")
    parser.add_argument("-c", dest='check', action='store_true', default=False, help="To verify firmware(After Reboot)")
    parser.add_argument("-a", dest='vintage', default='stable', help="To pass the firmware repo to be consumed like stable or latest")

    args = parser.parse_args()

    if not phaser.am_i_root():
        logging.warn("Phaser must be run with elevated privileges")
        sys.exit(errno.EPERM)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


    if args.update:
        start_time = time.time()
        logging.info("INFO: Checking if commands related to phaser have installed")
        if validate_commands():
            logging.info("INFO: Phaser related commands are present on host")
            logging.info("INFO: Validating, if firmware required an update")
            exit_status = validate_firmware(args.vintage)
            if exit_status:
                execute_firmware(args.vintage)
                if args.time_taken:
                    print("--- %s seconds ---" % (time.time() - start_time))
        else:
            logging.warn("ERROR: Phaser installation not found")

    elif args.check:
        logging.info("INFO: Validating firmware...")
        exit_status = validate_firmware(args.vintage)
        if exit_status:
            logging.warn("INFO: Firmware was not updated to latest")
            sys.exit(1)


