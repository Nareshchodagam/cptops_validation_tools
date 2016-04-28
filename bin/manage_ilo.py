#!/usr/bin/python
#
# manage_bootdevice.py
#
""" Set the bootdevice """

import logging
import os
import subprocess
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
        exit(1)


    print("Vendor identified as: " + vendor)
    return vendor

def factoryReset(vendor):
    # DELL Section
    if vendor == "DELL":
    
        rtrn_flag = False
        cmnds = ['/opt/dell/srvadmin/bin/idracadm7', '/opt/dell/srvadmin/bin/idracadm',
                     '/opt/dell/srvadmin/sbin/racadm']
        for command in cmnds:
            if os.path.exists(command):
                cmd = "{0} racresetcfg" .format(command)
                logging.debug("Executing command "+ cmd)
                result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = result.communicate()
                logging.debug(out.rstrip())
                if result.returncode == 0:
                    rtrn_flag = True
                    return True
                else:
                    continue
            else:
                continue
        return False

    # HP Section
    elif vendor == "HP":
        try:
            cmd="/sbin/hponcfg --reset"
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
        exit(1)    
        
        

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
            return True

        except:
            print('Unable to set boot device.')
            return False

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
    parser.add_option("-r", action="store_true", dest="resetdevice", default=False, help="Factory reset device")
    parser.add_option("-s", action="store_true", dest="setdevice", default=False, help="Set boot device")
    parser.add_option("-d", dest="devicename", help="Device (HDD or PXE)")


    (options, args) = parser.parse_args()
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if options.getvendor:
        vendor=getVendor()

    if options.setdevice:
        vendor=getVendor()
        if not setBootDev(vendor,options.devicename.upper()):
            print("Unable to set boot device")
            exit(1)
    if options.resetdevice:
        vendor=getVendor()
        factoryReset(vendor)

