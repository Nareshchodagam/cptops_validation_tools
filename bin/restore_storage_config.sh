#! /bin/bash

for vg in `cat ~/vg-list.txt` ; do vgchange -a y $vg ; done

