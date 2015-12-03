#!/usr/bin/python

import argparse
import logging
import re
import shlex
from subprocess import Popen,PIPE


def check_mtab(mount_point):
    with open('/etc/mtab', 'r') as f:
        logging.debug("Checking %s in /etc/mtab" %(mount_point))
        for line in f:
            if "%s" % (mount_point) in line:
                print("%s mount point has already mounted" %  (mount_point))
                exit(0)
            else:
                continue
        return False

def check_fstab(mount_point):
    if check_mtab(mount_point) is not True:
        with open('/etc/fstab', 'r') as f:
            logging.debug("Checking %s in /etc/fstab" % (mount_point))
            for line in f:
                if "%s" % (mount_point) in line and not line.startswith('#'):
                    print("%s mount point is present in fstab" % (mount_point))
                    cmd = shlex.split("mount %s" % (mount_point))
                    p = Popen(cmd, stdout=PIPE)
                    (out, err) = p.communicate()
                    print(out)
                    rtrn_code = p.returncode
                    return True
                    break
                else:
                    continue
            return False




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Verify the mount points')
    parser.add_argument("-m", dest="mount", help="Mount point name")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", help="verbose")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if args.mount:
        rtrn = check_fstab(args.mount)
        if rtrn is not True:
            print("May be someone has modify the fstab file, please check manually")
            exit(1)
        else:
            print("Mounted the %s" % args.mount)
            exit(0)
