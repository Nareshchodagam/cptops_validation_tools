#!/usr/bin/python
"""
Script to check if the /boot/grub.conf is a symlink to /boot/grub/grub.conf.
This has become a known issue for the search servers in production.
"""
import os
import platform
import shutil
import sys
import subprocess

BOOT_DIR = "/boot/grub/"
GRUB_DIR = "/etc/"
LS_CMD = "ls -ltr /etc/grub.conf"
DISTRO = platform.linux_distribution()

# Check for Centos 7 or higher, and exit if true. grub.conf doesn't have the same issues in newer versions of CentOS
if DISTRO[0] == 'CentOS Linux' and DISTRO[1][0] > 6:
    print 'This version of Linux uses grub2 or higher, I\'m not needed, here; exitting.'
    sys.exit(0)


if not os.path.islink(GRUB_DIR + "grub.conf"):
    print "%s/grub.conf is not a symlink to %s/grub/conf ...correcting" % (GRUB_DIR, BOOT_DIR)
    shutil.copy(BOOT_DIR + "grub.conf", BOOT_DIR + "grub.conf.bak")
    shutil.copy(GRUB_DIR + "grub.conf", GRUB_DIR + "grub.conf.bak")
    shutil.move(GRUB_DIR + "grub.conf", BOOT_DIR + "grub.conf")
    os.symlink(BOOT_DIR + "grub.conf", GRUB_DIR + "grub.conf")
else:
    sys.exit(0)

if os.path.islink(GRUB_DIR + "grub.conf"):
    subprocess.call(LS_CMD.split())
    sys.exit(0)
else:
    print "Symlink not valid."
    subprocess.call(LS_CMD.split())
    sys.exit(1)
