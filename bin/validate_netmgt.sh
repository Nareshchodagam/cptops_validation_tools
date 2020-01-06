#!/bin/bash

# validate_netmgt.sh

# remove stale lock files
ls -a /tmp/ | grep -Ew "$(hostname -s | awk -F - '{print $4}')(-mds|-f5).run.lock" | xargs -I {} rm -rf /tmp/{}
