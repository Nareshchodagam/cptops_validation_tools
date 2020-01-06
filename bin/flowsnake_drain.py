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

def exec_cmd(cmd, description, retries=0, interval_secs=5):
    retcode = subprocess.call(shlex.split(cmd))
    if retcode == 0:
        print "{} successful".format(description)
    else:
        if retries > 0:
            print "{} did not complete, {} attempt(s) remaining".format(description, retries)
            time.sleep(interval_secs)
            exec_cmd(cmd, description, retries-1, interval_secs)
        else:
            print "{} failed".format(description)
            print "{} -> {}".format(cmd, retcode)
            print "Failed with errors but ok to proceed per Flowsnake team."
            sys.exit(0)


def drain_node(description):
    '''

    :return:
    '''
    taint_cmd = "{KC} taint node {HOST} --overwrite {TAINT_KEY}={TIME}:NoExecute".format(**ENV)
    exec_cmd(taint_cmd, "Taint")
    label_cmd = "{KC} annotate node {HOST} --overwrite {TAINT_KEY}='{} started {TIME}'".format(description, **ENV)
    exec_cmd(label_cmd, "Label")
    # Wait for all terminating pods to finish rescheduling
    # First, wait briefly so Kubernetes Schduler has time to flag all pods that are to be terminated. In testing,
    # no delay was observable, so assume this happens quickly.
    time.sleep(3)
    # No kubectl --field-selector prior to Kubernetes 1.9 (https://github.com/kubernetes/kubernetes/pull/50140)
    await_cmd = "bash -c '! {KC} get pods --all-namespaces -o wide | grep {HOST} | grep Terminating'".format(**ENV)
    exec_cmd(await_cmd, "Reschedule", retries=10, interval_secs=5)


def rejoin_node():
    '''

    :return:
    '''
    # Check for existing taint first because command will fail otherwise
    untaint_cmd = "bash -c 'if {KC} get node {HOST} -o jsonpath=\"{{.spec.taints[?(@.key=={TAINT_KEY})].key}}\" | grep -q {TAINT_KEY}; then {KC} taint node {HOST} {TAINT_KEY}-; else echo \"Node already untainted.\"; fi'".format(**ENV)
    exec_cmd(untaint_cmd, "Untaint")
    # Annotation removal is idempotent; no need to check if already present.
    unlabel_cmd = "{KC} annotate node {HOST} {TAINT_KEY}-".format(**ENV)
    exec_cmd(unlabel_cmd, "Unlabel")


def iso8601_stamp():
    return re.sub(r":\d\d\.\d*", "Z", datetime.datetime.utcnow().isoformat()).replace(":", "") # 2018-08-13T10:19:39.869467 ->  2018-08-13T1019Z


ENV={
    'KC': "kubectl --kubeconfig=/etc/kubernetes/kubeconfig",
    'HOST': socket.gethostname(),
    'TAINT_KEY': "PatchingInProgress",
    'TIME': iso8601_stamp()
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Case Builder Program   ")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("-d", "--drain", dest="drain", action="store_true", help="Drain node.")
    mode_group.add_argument("-r", "--rejoin", dest="rejoin", action="store_true", help="Rejoin node back to cluster")
    parser.add_argument("-b", "--bundle", dest="bundle", required="-d" in sys.argv or "--drain" in sys.argv, help="Patch bundle being applied (human-readable description)")
    options = parser.parse_args()

    if options.drain:
        drain_node(options.bundle)
    elif options.rejoin:
        rejoin_node()
