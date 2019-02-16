#!/bin/bash
# Written by Funnel team (fka Ajna Ingestion)

FQDN="$(hostname -f)"

PATTERN=\"status\"\ :\ \"UP\"

PREFIX=:15380\/manage\/health

CHECK_STATUS_UP="$(curl -s  http:\/\/$FQDN$PREFIX | grep -o "$PATTERN" | wc -l)"


if [ "$CHECK_STATUS_UP" = "4" ]
	then 
	echo "Funnel :        [RUNNING]"
else
	echo "ERROR Funnel :        [NOT RUNNING]"
	exit 1
fi
