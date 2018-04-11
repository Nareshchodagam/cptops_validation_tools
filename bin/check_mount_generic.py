#!/usr/bin/python

import argparse
import logging
import re
import shlex
from subprocess import Popen,PIPE
import sys
import os
import time


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


def mount_filesystem(mount_point):
    '''
    Function to mount the filesystem.
    :param mount_point:
    :return:
    '''
    cmd = shlex.split("mount %s" % (mount_point))
    p = Popen(cmd, stdout=PIPE)
    (out, err) = p.communicate()
    print(out)
    rtrn_code = p.returncode
    if rtrn_code != 0:
        print("Failed to mount {} filesystem.").format(mount_point)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Verify the mount points')
    parser.add_argument("-f", dest="filesystem", help="Filesystem to check")
    parser.add_argument("-m", action="store_true", dest="mount", help="Perform a mount.")
    parser.add_argument("-c", "--check", action="store_true", dest="check", help="Check mount")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", help="verbose")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if args.check and not args.filesystem:
        print("Missing mounpoint to check")
        sys.exit(1)
    elif args.check and args.filesystem:
        counter = 0
        while (counter != 3):
            if os.path.ismount(args.filesystem):
                print " %s filesystem is mounted" % (args.filesystem)
                sys.exit(0)
            counter += 1
            time.sleep(60)
        sys.exit(1)

    if args.filesystem:
        rtrn = check_fstab(args.filesystem)
        if rtrn is not True:
            print("May be someone has modify the fstab file, please check manually")
            exit(1)
        else:
            print("Mounted the %s" % args.filesystem)
            exit(0)
