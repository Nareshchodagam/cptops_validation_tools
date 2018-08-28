#!/usr/bin/python

import os
import sys
import time

retries = 3
backup_running = False

for i in range(retries):
	processes = os.popen('ps -ef | grep [d]oBackup').read()   
	if len(processes) == 0:
		print 'Backup job is not running.'
		sys.exit(0)
	else:
		time.sleep(3*60)
		print 'Backup job is running. Retry.'

print 'Backup job is still running after retries. Exiting....'
sys.exit(1)
