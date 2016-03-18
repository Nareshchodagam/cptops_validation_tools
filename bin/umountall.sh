#! /bin/bash

MOUNTSS=$1
usage() {
    echo "specify mount search string eg '/hub/'"
}


if [-z $MOUNTSS ];then
  usage
  exit 1
fi
mount | grep "$MOUNTSS" | awk '{print $3}' | while read MYF; do echo "unmounting $MYF"; umount $MYF; done; umount /hub || exit 1
