#!/bin/bash
statusFile="/opt/app/smszk/status"
cDateTime=`/usr/bin/date +%Y%m%d%H%M`
ftime=`stat -c%y $statusFile | awk -F - '{print $1$2$3}' | awk -F : '{print $1$2}' | awk '{print $1$2}'`
status="OK"
diffTime=$(($cDateTime - $ftime))

echo "Datetime $cDateTime"
echo "File mod time $ftime"
echo "diff time $diffTime"


for i in {1..300}                                                                                                                                                                                                                                                                     
do
    if [ ! -f "$statusFile" ]; then
          echo "File $statusFile not Found!"
          exit 1
      fi
    input=`cat $statusFile`
    sleep $i
    echo "Sleeping for $i sec..."
      if [ "$input" == "$status" ]; then
          if [ "$diffTime" -le 300 ]; then
            echo $input
            exit 0
            break
          else
            echo "Found $input but file is $diffTime seconds old."
            exit 1
            break
          fi
      else
          echo $input
      fi
done
