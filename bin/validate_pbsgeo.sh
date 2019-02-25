#!/bin/bash

echo "Calling... validateDeployment.jsp"
result=$(curl http://localhost:8080/validateDeployment.jsp)

if [ $? -eq 0 ] && [[ $result == *"geocoding.v1 responds as expected"* ]]
then
  echo "[Succeed]"
  exit 0
else
  echo "[Failed]"
  exit 1
fi
