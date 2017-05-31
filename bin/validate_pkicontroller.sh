#!/bin/bash

PKIUSER=pkisvc
sudo "/home/${PKIUSER}/bin/validate_pkicontroller.sh"
if [ $? -ne 0 ]
then
		echo "Validation failed"
		exit 1
else
		echo "Validation succeeded"
		exit 0
fi
