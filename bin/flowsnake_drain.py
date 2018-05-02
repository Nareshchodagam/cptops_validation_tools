#!/usr/bin/python
#
#
import re
import subprocess
import argparse
import sys
import shlex
import socket

def check_master():
    '''

    :return:
    '''
    host_chk = re.compile(r'.*(master).*')
    if host_chk.findall(socket.gethostname()):
        return False
    else:
        return True

def drain_node():
    '''

    :return:
    '''
    kube_cmd = "kubectl --kubeconfig=/etc/kubernetes/kubeconfig drain --ignore-daemonsets --delete-local-data {}".format(socket.gethostname())
    retcode = subprocess.call(shlex.split(kube_cmd))
    if retcode == 0:
        print "Node drained succesfully."
        sys.exit(0)
    else:
        print "Node failed to drain succesfully"
        sys.exit(1)

def rejoin_node():
    '''

    :return:
    '''
    rejoin_cmd = "kubectl --kubeconfig=/etc/kubernetes/kubeconfig uncordon {}".format(socket.gethostname())
    retcode = subprocess.call(shlex.split(rejoin_cmd))
    if retcode == 0:
        print "Node rejoin successful."
        sys.exit(0)
    else:
        print "Node rejoin failed"
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Case Builder Program   ")
    parser.add_argument("-r", "--rejoin", dest="rejoin", action="store_true", help="Rejoin node back to cluster")
    options = parser.parse_args()

    if options.rejoin:
        rejoin_node()
    else:
        response = check_master()
        if response:
            drain_node()
        else:
            print "Node is not a worker node. Skipping the drain process..."
            sys.exit(0)