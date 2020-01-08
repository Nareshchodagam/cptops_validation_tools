#!/bin/bash
#KFORA App validation script

for i in healthCheck certCheck ping.jsp; do curl -k https://localhost:8443/$i && echo ":::$i on `uname -n | cut -d"." -f1`"; done
