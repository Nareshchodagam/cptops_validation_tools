#!/bin/bash

curlHttp() {
  local url
  url="http://localhost:8080/${1}"
  shift || return # function should fail if we weren't passed at least one argument
  echo "Calling... curl $url"
  curl "$url"
}

curlHttp validateDeployment.jsp
if [ $? -eq 0 ]
then
  echo "[Succeed]"
  exit 0
else
  echo "[Failed]"
  exit 1
fi
