#!/usr/bin/python
#
# manage_bootdevice.py
#
""" Set the bootdevice """

import logging
import os
import subprocess
import sys
from optparse import OptionParser


path = '/opt/dell/srvadmin/sbin/'
os.environ['PATH'] += os.pathsep + path


def getVendor():

    logging.debug('Checking dmidecode to identify vendor')

    try:
        cmd="dmidecode | grep Vendor | awk '{print $2}'"
        result=subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out,err=result.communicate()
        vendor=out.upper().strip()

        logging.debug("OUT: " + out.rstrip())
        logging.debug("ERR: " + err.rstrip())

    except:
        print('Unable to identify vendor')
        sys.exit(1)


    print("Vendor identified as: " + vendor)
    return vendor

def setBootDev(vendor,device):
    logging.debug('Setting ' + vendor + ' device to boot from ' + device)


    # DELL Section
    if vendor == "DELL":

        if device.upper() == "PXE":
            persistence=1
        else:
            persistence=0


        logging.debug('Setting persistence to : ' + str(persistence))

        rtrn_flag = False
        cmnds = ['/opt/dell/srvadmin/bin/idracadm7', '/opt/dell/srvadmin/bin/idracadm',
                 '/opt/dell/srvadmin/sbin/racadm']

        for command in cmnds:
            if os.path.exists(command):
                cmd = "{0} config -g  cfgServerInfo -o cfgServerBootOnce {1}" .format(command, str(persistence))
                logging.debug("Executing command "+ cmd)
                cmd1 = "{0} config -g cfgServerInfo -o cfgServerFirstBootDevice {1}" .format(command, device)
                result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = result.communicate()
                logging.debug(out.rstrip())
                if result.returncode == 0:
                    rtrn_flag = True
                    logging.debug("Executing command " + cmd1)
                    result = subprocess.Popen(cmd1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out, err = result.communicate()
                    logging.debug(out.rstrip())
                    return True
                else:
                    continue
            else:
                continue
        return False


    # HP Section
    elif vendor in ("HP","HPE"):
        if device.upper() == "PXE":
            type='once'
        else:
            type='first'

        try:
            cmd="hpasmcli -s 'set boot " + type + " " + device + "'"
            logging.debug('Executing command: ' + cmd)
            result=subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out,err=result.communicate()
            print(out.rstrip())
            return True

        except:
            print('Unable to set boot device.')
            return False

    else:
        print("Unidentified vendor: " + vendor)
        sys.exit(0)

def resetConsole():

    logging.debug('resetting the console')

    reset_flag = False

    cmnds = ['/opt/dell/srvadmin/bin/idracadm7', '/opt/dell/srvadmin/bin/idracadm',
                 '/opt/dell/srvadmin/sbin/racadm']

    #Loop through the commands List and find the return code
    for command in cmnds:
        if os.path.exists(command):
            cmd = "{0} racreset soft".format(command)
            logging.debug("Executing command "+ cmd)
            result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = result.communicate()
            logging.debug(out.rstrip())
            if result.returncode == 0:
                reset_flag = True
    #validate the reset flag if it is False then System Exit
    if not reset_flag:
        print("Unable to RESET the console, Performing Exit ")
        sys.exit(1)


if __name__ == "__main__":

    usage="""

    %prog
    ------------------------------------------------------------------------

    # Get hardware vendor of running host
    %prog -g

    # Set boot device
    %prog -s -d [HDD|PXE]

    ------------------------------------------------------------------------

    """

    parser = OptionParser(usage)
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="Verbosity")
    parser.add_option("-g", action="store_true", dest="getvendor", default=False, help="Get vendor")
    parser.add_option("-s", action="store_true", dest="setdevice", default=False, help="Set boot device")
    parser.add_option("-d", dest="devicename", help="Device (HDD or PXE)")
    parser.add_option("-r", action="store_true", dest="reset", help="reset the console")


    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if options.getvendor:
        vendor=getVendor()

    if options.reset:
        vendor=getVendor()
        if vendor.upper() == "DELL":
            resetConsole()

    if options.setdevice:
        vendor=getVendor()
        if not setBootDev(vendor,options.devicename.upper()):
            print("Unable to set boot device")
            # print error, exit anyway.  This will help with CaPTain.
            sys.exit(0)

