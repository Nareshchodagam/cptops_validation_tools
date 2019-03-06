#!/bin/bash

curlHttp() {
  local url
  url="http://localhost:8080/${1}"
  shift || return # function should fail if we weren't passed at least one argument
  curl -s "$url"
}
echo "Calling... validateDeployment.jsp"

result=$(curlHttp validateDeployment.jsp)
count=$(echo $result | grep -o 'responds as expected' | wc -l)

if [[ $? -eq 0 && ($count -eq 11)]]
then
  echo "PBSMatch validation passed with output: $result"
  exit 0
else
  echo "PBSMatch validation failed with output: $result"
  exit 1
fi
