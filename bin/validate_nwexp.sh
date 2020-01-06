#!/bin/bash
ps aux | egrep -i 'sflow_mux|sflowexp_[0-2]|zookeeper' |grep -v grep
