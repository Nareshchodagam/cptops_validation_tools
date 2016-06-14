#!/usr/bin/python
#
# manage_bootdevice.py
#
""" Set the bootdevice """

import logging
import os
import subprocess
from optparse import OptionParser
import time



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

def deviceInfoB(vendor):
    # get device info Before factory reset
    # DELL Section
    if vendor == "DELL":

        dump_file = '/tmp/drac-dump-pre.txt'

        rtrn_flag = False
        cmnds = ['/opt/dell/srvadmin/bin/idracadm7', '/opt/dell/srvadmin/bin/idracadm',
                     '/opt/dell/srvadmin/sbin/racadm']
        for command in cmnds:
            if os.path.exists(command):
                cmd = "{0} getsysinfo >> %s" .format(command) % (dump_file)
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

        dump_file = '/tmp/ilo-dump-pre.xml'

        try:
            cmd="/sbin/hponcfg -a -w %s" % (dump_file)
            logging.debug('Executing command: ' + cmd)
            result=subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out,err=result.communicate()
            print(out.rstrip())
            return True

        except:
            print('Unable to get device info.')
            return False
    else:
        print("Unidentified vendor: " + vendor)
        exit(1)

def factoryReset(vendor):
    # factory reset    
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

        if os.path.exists('/tmp/ilo-dump-pre.xml'):
            print "Good to proceed with factory reset"
        else:
            print "Re-run step to get device info before factory reset"
            deviceInfoB(vendor)
            factoryReset(vendor)

        try:
            cmd="/sbin/hponcfg --reset"
            logging.debug('Executing command: ' + cmd)
            result=subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out,err=result.communicate()
            print(out.rstrip())
            return True

        except:
            print('Unable to reset device to default.')
            return False
    else:
        print("Unidentified vendor: " + vendor)
        exit(1)    

def deviceInfoA(vendor):
    # get device info After factory reset
    # DELL Section
    if vendor == "DELL":
        #pause for 30 secs to allow DRAC reset
        time.sleep(30)
        dump_file = '/tmp/drac-dump-post.txt'

        rtrn_flag = False
        cmnds = ['/opt/dell/srvadmin/bin/idracadm7', '/opt/dell/srvadmin/bin/idracadm',
                     '/opt/dell/srvadmin/sbin/racadm']
        for command in cmnds:
            if os.path.exists(command):
                cmd = "{0} getsysinfo >> %s" .format(command) % (dump_file)
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

        dump_file = '/tmp/ilo-dump-post.xml'
        #pause for 60 secs to allow DRAC reset
        time.sleep(60) 

        try:
            cmd="/sbin/hponcfg -a -w %s" % (dump_file)
            logging.debug('Executing command: ' + cmd)
            result=subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out,err=result.communicate()
            print(out.rstrip())
            return True

        except:
            print('Unable to get device info.')
            return False
    else:
        print("Unidentified vendor: " + vendor)
        exit(1)

def deviceCheck(vendor):
    # confirm factory reset
    # DELL Section
    if vendor == "DELL":

        #select values to check drac_dump_pre vs. drac_dump_post
        drac_value = ["Host Name", "Current IP Address", "Current DNS Domain"]
        #Store drac_dump_pre Name:Value
        drac_pre = []
        #Store drac_dump_post Name:Value
        drac_post = []

        #get values from drac_dump_pre file
        with open('/tmp/drac-dump-pre.txt', 'r') as drac_dump_pre:
            try:
                for line in drac_dump_pre:
                    for item in drac_value:
                        if item in line:
                            item_name = line.split('=')[0]
                            item_name_nospace = item_name.strip()
                            item_value = line.split('=')[1]
                            item_value_nospace = item_value.strip()
                            if item == item_name_nospace:
                                drac_pre.append(item_name_nospace + ':' + item_value_nospace)
            except Exception as e:
                print('Problem loading file %s : %s' % (drac_dump_pre,e))
         
        #get values from drac_dump_post file
        with open('/tmp/drac-dump-post.txt', 'r') as drac_dump_post:
            try:
                for line in drac_dump_post:
                    for item in drac_value:
                        if item in line:
                            item_name = line.split('=')[0]
                            item_name_nospace = item_name.strip()
                            item_value = line.split('=')[1]
                            item_value_nospace = item_value.strip()
                            if item == item_name_nospace:
                                drac_post.append(item_name_nospace + ':' + item_value_nospace)
            except Exception as e:
                print('Problem loading file %s : %s' % (drac_dump_post,e))

        #confirm values are different i.e factoryReset completed succesfully
        u = set(drac_pre).union(set(drac_post))
        i = set(drac_pre).intersection(set(drac_post))
        diff = list(u - i)
        if not diff:
            print 'Factory reset unsuccessful, pre and post still match: \n pre \n %s  \n and post \n %s' % (drac_pre,drac_post)
            exit(1)
        else:
            print 'Factory reset successful: \n pre \n %s  \n and post \n %s' % (drac_pre,drac_post)
            exit(0)
               
    # HP Section
    elif vendor == "HP":

        if os.path.exists('/tmp/ilo-dump-post.xml'):
            print "Good to proceed with factory default check"
        else:
            print "Re-run step to get device info after factory reset"
            deviceInfoA(vendor)
            deviceCheck(vendor)

        #select values to check drac_dump_pre vs. drac_dump_post
        ilo_value = ["<DNS_NAME VALUE", "<IP_ADDRESS VALUE", "<DOMAIN_NAME VALUE"]
        #Store ilo_dump_pre Name:Value
        ilo_pre = []
        #Store ilo_dump_post Name:Value
        ilo_post = []

        #get values from ilo_dump_pre file
        with open('/tmp/ilo-dump-pre.xml', 'r') as ilo_dump_pre:
            try:
                for line in ilo_dump_pre:
                    for item in ilo_value:
                        if item in line:
                            item_name = line.split('=')[0]
                            item_name_nospace = item_name.strip()
                            item_value = line.split('=')[1]
                            item_value_nospace = item_value.strip()
                            if item == item_name_nospace:
                                ilo_pre.append(item_name_nospace + ':' + item_value_nospace)
            except Exception as e:
                print('Problem loading file %s : %s' % (ilo_dump_post,e))

        #get values from ilo_dump_post file
        with open('/tmp/ilo-dump-post.xml', 'r') as ilo_dump_post:
            try:
                for line in ilo_dump_post:
                    for item in ilo_value:
                        if item in line:
                            item_name = line.split('=')[0]
                            item_name_nospace = item_name.strip()
                            item_value = line.split('=')[1]
                            item_value_nospace = item_value.strip()
                            if item == item_name_nospace:
                                ilo_post.append(item_name_nospace + ':' + item_value_nospace)
            except Exception as e:
                print('Problem loading file %s : %s' % (ilo_dump_post,e))

        #confirm values are different i.e factoryReset completed succesfully
        u = set(ilo_pre).union(set(ilo_post))
        i = set(ilo_pre).intersection(set(ilo_post))
        diff = list(u - i)
        if not diff:
            if ilo_pre[1].split('"')[1] == "":
                print 'Factory reset already completed: \n pre \n %s  \n and post \n %s' % (ilo_pre,ilo_post)
                exit(0) 
            else:
                print 'Factory reset unsuccessful, pre and post still match: \n pre \n %s  \n and post \n %s' % (ilo_pre,ilo_post)
                print 'Retry factory reset and re-check'                
                os.remove('/tmp/ilo-dump-post.xml') 
                factoryReset(vendor)
                deviceInfoA(vendor)
                deviceCheck(vendor) 
        else:
            print 'Factory reset successful: \n pre \n %s  \n and post \n %s' % (ilo_pre,ilo_post)
            exit(0)

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
    parser.add_option("-b", action="store_true", dest="getsysinfoB", default=False, help="Factory reset pre/before")
    parser.add_option("-r", action="store_true", dest="resetdevice", default=False, help="Factory reset device")
    parser.add_option("-a", action="store_true", dest="getsysinfoA", default=False, help="Factory reset post/after")
    parser.add_option("-c", action="store_true", dest="checkdevice", default=False, help="Factory reset confirm")
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

    if options.getsysinfoB:
        vendor=getVendor()
        deviceInfoB(vendor)

    if options.resetdevice:
        vendor=getVendor()
        factoryReset(vendor)

    if options.getsysinfoA:
        vendor=getVendor()
        deviceInfoA(vendor)

    if options.checkdevice:
        vendor=getVendor()
        deviceCheck(vendor)        
