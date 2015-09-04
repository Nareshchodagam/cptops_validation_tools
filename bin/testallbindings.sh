#!/bin/bash

##########################################################################
# Run this script on an MTA to send a mail out on each outbound binding. #
# Script updated 7/29/15
##########################################################################

if [ -z "$1" -o "$1" == "-h" -o "$1" == "--help" ]; then
    echo "$0 recipient [ ... recipient ]"
    exit 1
fi


for BINDING in \
    bounce-1 \
    site-relay-1 \
    system-1 \
    service-1 \
    org-direct-a-1-1 \
    org-direct-a-2-1 \
    org-direct-a-3-1 \
    org-direct-b-1-1 \
    org-direct-b-1-2 \
    org-direct-b-1-3 \
    org-direct-b-1-4 \
    org-direct-b-2-1 \
    org-direct-b-2-2 \
    org-direct-b-3-1 \
    org-direct-b-3-2 \
    org-direct-b-3-3 \
    org-direct-b-3-4 \
    org-direct-c-1-1 \
    org-direct-c-2-1 \
    org-direct-c-3-1 \
    gack-1 \
    org-relay-1
do
    /opt/msys/ecelerity/bin/ec_sendmail -F EmailInfrastrucutre -f emailinfrastructure@salesforce.com $@ <<EOF
Subject: testing binding $BINDING
X-SFDC-Binding: $BINDING
X-SFDC-Test-Binding: None

Testing binding $BINDING.
EOF
done
