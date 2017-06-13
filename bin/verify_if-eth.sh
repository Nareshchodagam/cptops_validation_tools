#!/bin/bash
echo "Verifying cksum..."
if [[ $(cksum /etc/sysconfig/network-scripts/ifdown-eth | awk "{print \$1}")  == 1209049645 ]] 
then
	echo "CKSUM Matches"
	exit 0
else
	echo "CKSUM Doesn't Match"
	exit 1
fi
