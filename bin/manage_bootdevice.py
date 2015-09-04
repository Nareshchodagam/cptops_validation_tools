#!/usr/bin/python
#
# manage_bootdevice.py
#
""" Set the bootdevice """

import logging
import os
import subprocess
from optparse import OptionParser


def getVendor():

    logging.debug('Checking dmidecode to identify vendor')

    try:
        cmd="dmidecode | head -15 | grep Vendor | awk '{print $2}'"
        result=subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out,err=result.communicate()
        vendor=out.upper().strip()

        logging.debug("OUT: " + out.rstrip())
        logging.debug("ERR: " + err.rstrip())

    except:
        print('Unable to identify vendor')
        exit(1)


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
        try:   
            cmd="racadm config -g cfgServerInfo -o cfgServerBootOnce " + str(persistence)
            result=subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out,err=result.communicate()
            logging.debug(out.rstrip())
        except:
            print('Unable to set to boot persistence to ' + str(persistence))
            exit(1)
    
        logging.debug('Setting first boot device to: ' + device)
        try:
            cmd="racadm config -g cfgServerInfo -o cfgServerFirstBootDevice " + device
            result=subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out,err=result.communicate()
            logging.debug(out.rstrip())
            print('Successfully set first boot device to ' + device)
        
        except:
            print('Unable to set boot device.')
            exit(1)

    # HP Section
    elif vendor == "HP":
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

        except:
            print('Unable to set boot device.')
            exit(1)
    else:
        print("Unidentified vendor: " + vendor)
        exit(1)


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


    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if options.getvendor:
        vendor=getVendor()

    if options.setdevice:
        vendor=getVendor()
        setBootDev(vendor,options.devicename.upper())


