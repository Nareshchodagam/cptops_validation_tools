#!/usr/bin/python
###############################################################################
#
# Author:  mhealy
# Purpose: 3 options:
#          Set iDB operationalStatus to "DECOM"
#          iDB Reset
#          Remove from iDb 
#
###############################################################################

import argparse
import sys
import os

# inventory-action.pl dir
ia_dir = '/home/sfdc/current/dca-inventory-action/dca-inventory-action/'
# update managed hosts
ia_um = 'inventory-action.pl -action update -resource host -name '
# update unmanaged hosts
ia_uu = 'inventory-action.pl -action update -resource unmanagedhost -name '

def update_idb(host_list):

	# update host operationalStatus
	ia_Fs = ' -updateFields "operationalStatus=DECOM"'

	# attempts both managed and unmanaged 
	for host in host_list:
		os.system (ia_dir + ia_um + host + ia_Fs + "> /dev/null 2>&1")
		os.system (ia_dir + ia_uu + host + ia_Fs + "> /dev/null 2>&1")

def reset_idb(host_list):

	# set operationalStatus to HW_PROVISIONING
	ia_Fs = ' -updateFields "operationalStatus=HW_PROVISIONING"'
	# set deviceRole to null
	ia_Fd = ' -updateFields "deviceRole=null"'
	# set (host) name to null
	ia_Fn = ' -updateFields "name=null"'

	# attempts both managed and unmanaged 
	for host in host_list:
		os.system (ia_dir + ia_um + host + ia_Fs + "> /dev/null 2>&1")
		os.system (ia_dir + ia_um + host + ia_Fd + "> /dev/null 2>&1")
		os.system (ia_dir + ia_um + host + ia_Fn + "> /dev/null 2>&1")
		os.system (ia_dir + ia_uu + host + ia_Fs + "> /dev/null 2>&1")
		os.system (ia_dir + ia_uu + host + ia_Fd + "> /dev/null 2>&1")
		os.system (ia_dir + ia_um + host + ia_Fn + "> /dev/null 2>&1")

def delete_idb(host_list):

	# delete managed hosts
	ia_dm = 'inventory-action.pl -action delete -resource host -name '
	# delete unmanaged hosts
	ia_du = 'inventory-action.pl -action delete -resource unmanagedhost -name '

	# attempts both managed and unmanaged 
	for host in host_list:
		os.system (ia_dir + ia_dm + host + "> /dev/null 2>&1")
		os.system (ia_dir + ia_du + host + "> /dev/null 2>&1")

###############################################################################
#                Main
###############################################################################

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description="Script to update iDb for host DECOM")

	parser.add_argument("-H", "--host", dest="hostlist",
		help="provide comma separated host list")

	parser.add_argument("-o", "--option", dest="option",
		help="[-u] set the host operationalStatus field to \"DECOM\" [-r] reset host in iDb name,Status,deviceRole,cluster [-d] delete the host entry from iDB") 

	args = parser.parse_args()

	# create array 'host_list' from hosts provided	
	host_list = [str(item) for item in args.hostlist.split(',')]
	# option
	idb_option = args.option

	# pass 'host_list' to correct function depending on 'idb_option' value
	if idb_option == 'u':
		update_idb(host_list)
	elif idb_option == 'r':
		reset_idb(host_list)
	elif idb_option == 'd':
		delete_idb(host_list)
	else:
		print '''Please enter a valid option:
		[-u] set the host operationalStatus field to \"DECOM\" 
		[-r] reset host in iDb - name,operationalStatus,deviceRole,cluster 
		[-d] delete the host entry from iDB")
		Ex. /decomm_idb.py -H <host_name1>,<host_name2> -o r '''
