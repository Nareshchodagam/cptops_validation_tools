#!/bin/bash

echo "Calling... validateDeployment.jsp"
result=$(curl http://localhost:8080/validateDeployment.jsp)

if [ $? -eq 0 ] && [[ $result == *"geocoding.v1 responds as expected"* ]]
then
  echo "PBSGeo validation passed with output: $result"
  exit 0
else
  echo "PBSGeo validation failed with output: $result"
  exit 1
fi
