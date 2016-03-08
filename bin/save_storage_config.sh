#! /bin/bash

# save fs config

VGLIST=~/vg-list.txt
LVLIST=~/lv-list.txt
VGBCK=~/vg.bck
LVBCK=~/lv.bck
DFBCK=~/df.bck
FSTABBCK=~/fstab.bck

df -h > $DFBCK
cp /etc/fstab $FSTABBCK
vgdisplay > $VGBCK
lvdisplay > $LVBCK
df |grep dev|cut -f 1|cut -d "/" -f 4|cut -d "-" -f 1 >> $VGLIST
df |grep dev|cut -f 1|cut -d "/" -f 4|cut -d "-" -f 2 >> $LVLIST

ls -al $VGLIST 

ls -al $LVLIST 

ls -al $VGBCK 

ls -al $LVBCK 

ls -al $DFBCK 

ls -al $FSTABBCK 

