#!/usr/bin/python
"""
script to append appropriate fix to the current kernel line in grub for HP database boxes and lhub boxes
"""
import os
import shutil
import sys
import subprocess
import re

KERNELMATCH='^[^#].*kernel.*vmlinuz-'
HPWORKAROUND=' loglevel=1 log_buf_len=8M'
GRUB_DIR = "/boot/grub/"
OUT = GRUB_DIR + 'grub.conf'
IN = OUT + '.bck_hp_soft' 
HPCHECK = "dmidecode | grep -i vendor | awk '{print $2}'"
CHECKGRUB = "cat " + OUT
modified = False
vendor = os.popen(HPCHECK).readlines()[0].rstrip('\n')

if vendor != 'HP':
   print 'Not a hp box, no change needed'
   sys.exit(0)
else:
   shutil.copy(OUT,IN)


with open(OUT, 'w') as out_file:
    with open(IN, 'r') as in_file:
        for line in in_file:
            if re.match(KERNELMATCH,line) and not modified:
                out_file.write(line.rstrip('\n') + HPWORKAROUND + '\n')
                print 'mod made'
                modified = True
            else:
                out_file.write(line)

currentgrub = os.popen(CHECKGRUB).readlines()

for line in currentgrub:
    print line.rstrip('\n')

sys.exit(0)

