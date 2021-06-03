#!/usr/bin/env python

"""
    title - To remove lock files after rancid service run's post reboot 
    Author - CPT - cptops@salesfore.com
    Status - Active
    Created - 06-01-2021

"""
import os
import socket
import re

temp_dir='/tmp/'
datacenter = socket.gethostname().split('-')[3].split('.')[0]
pattern = re.compile(".{}(-md5|-f5).run.lock".format(datacenter))
files_paths=[]
for root, directories, files in os.walk(temp_dir):
    for file in files:
        if pattern.match(file):
            files_paths.append(os.path.join(root,file))
if files_paths:
    for file in files_paths:
        print("Removing lock file {}".format(file))
        os.remove(file)
else:
    print("No lock file present")
