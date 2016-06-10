#!/usr/bin/python
###############################################################################
#
# Author:  mhealy
# Purpose: Verify serial numbers match before proceeding with the decomm
#
###############################################################################

import argparse
import sys
import os

def compare(host_list):

	home_dir = os.getenv('HOME')
	gus_list = []
	rr_list = []

	# Pull out host and serial# from gus decomm file currently processed by rr
	for host in host_list:
		try:
			with open('%s/serial_check.txt' % (home_dir)) as gus_file:
				for line in gus_file:
					if host in line:
						gus_list.append(line.strip('\n'))						
		except IOError as e:
			print('Problem loading serial_check.txt, is the file in your home dir? \n %s' % (e))
			sys.exit(1)
				 								
	# Pull out host and serial# that rr pulled from the actual host				
	for host in gus_list:
		try:
			with open('/tmp/serial.txt') as rr_output:
				for line in rr_output:
					if host in line:
						line_fix1 = line.split('@')[1]
						line_fix2 = line_fix1.rstrip()
						rr_list.append(line_fix2.strip('\n'))
		except IOError as e:
			print('Problem loading serial.txt, is the file in your home dir? \n %s' % (e))
			sys.exit(1)						
	
	# Diff gus_list and rr_list				
	u = set(gus_list).union(set(rr_list))
	i = set(gus_list).intersection(set(rr_list))
	diff = list(u - i)
	if not diff:
		print 'Proceed with decomm, serial numbers match'
		sys.exit(0)
	else:
		print 'Please stop decomm, investigate serial number mismatch for %s' % (diff)
		sys.exit(1)

###############################################################################
#                Main
###############################################################################

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description="verify serial number")
	parser.add_argument("-H", "--host", dest="hostlist",
		help="compare two files, RR file and Decomm file", metavar="HOST")

	args = parser.parse_args()

	# create array 'host_list' from hosts passed into rr
	host_list = [str(item) for item in args.hostlist.split(',')]
	
	# pass 'host_list' to compare function to check serial numbers
	compare(host_list)
