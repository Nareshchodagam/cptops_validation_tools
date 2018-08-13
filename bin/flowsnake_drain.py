#!/usr/bin/python
#
#
import re
import subprocess
import argparse
import sys
import shlex
import socket
import datetime
import time

ENV={
    'KC': "kubectl --kubeconfig=/etc/kubernetes/kubeconfig",
    'HOST': socket.gethostname(),
    'TAINT_KEY': "PatchingInProgress"
}


def exec_cmd(cmd, description, retries=0, interval_secs=5):
    retcode = subprocess.call(shlex.split(cmd))
    if retcode == 0:
        print "{} successful".format(description)
    else:
        if retries > 0:
            print "{} failed, {} attempt(s) remaining".format(description, retries)
            time.sleep(interval_secs)
            exec_cmd(cmd, description, retries-1, interval_secs)
        else:
            print "{} failed".format(description)
            print "{} -> {}".format(cmd, retcode)
            sys.exit(1)


def drain_node(description):
    '''

    :return:
    '''
    kube_cmd = "{KC} taint node {HOST} --overwrite {TAINT_KEY}={}:NoExecute".format(description, **ENV)
    exec_cmd(kube_cmd, "Taint")
    # Await for all terminating pods to finish rescheduling
    # No kubectl --field-selector prior to Kubernetes 1.9 (https://github.com/kubernetes/kubernetes/pull/50140)
    await_cmd = "bash -c '! {KC} get pods --all-namespaces -o wide | grep {HOST} | grep Terminating'".format(**ENV)
    exec_cmd(await_cmd, "Reschedule", retries=10)


def rejoin_node():
    '''

    :return:
    '''
    # Check for existing taint first because command will fail otherwise
    rejoin_cmd = "bash -c 'if {KC} get node {HOST} -o jsonpath=\"{{.spec.taints[*].key}}\" | grep -q {TAINT_KEY}; then {KC} taint node {HOST} {TAINT_KEY}:NoExecute-; else echo \"Node already joined.\"; fi'".format(**ENV)
    exec_cmd(rejoin_cmd, "Join")



def iso8601_stamp():
    return re.sub(r":\d\d\.\d*", "Z", datetime.datetime.utcnow().isoformat()).replace(":", "") # 2018-08-13T10:19:39.869467 ->  2018-08-13T1019Z

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Case Builder Program   ")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("-d", "--drain", dest="drain", action="store_true", help="Drain node.")
    mode_group.add_argument("-r", "--rejoin", dest="rejoin", action="store_true", help="Rejoin node back to cluster")
    parser.add_argument("--description", dest="description", default=iso8601_stamp(), help="Description. (Recommended: patch bundle being applied; default: timestamp)", metavar="DESC")
    options = parser.parse_args()

    if options.drain:
        drain_node(options.description)
    elif options.rejoin:
        rejoin_node()
