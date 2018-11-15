#!/usr/bin/env python

import sys
import subprocess
import shlex
import re
import traceback
import socket
import collections
import threading


class Command(object):
    def __init__(self, cmd):
        self.cmd = shlex.split(cmd)
        self.process = None
        self.output = None
        self.status = None
        self.error = None

    def run(self, timeout=None):
        def target():
            try:
                self.process = subprocess.Popen(self.cmd,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE)
                self.output, self.error = self.process.communicate()
                self.status = self.process.returncode
            except:
                self.error = traceback.format_exc()
                self.status = -1

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            print 'Timeout - Terminating process.'
            self.process.terminate()
            thread.join()

        return (self.status, self.output, self.error)


def Validate(command, timeout,
             expected_output_pattern='', expected_exit_status=0):

    print 'Executing: ', command

    cmd = Command(command)
    (actual_status, actual_output, error) = cmd.run(timeout)

    if actual_status is not expected_exit_status:
        if error and error is not '':
            print 'Execution failed, reason: ', error
        else:
            print 'Execution failed, reason: ', actual_output
        return False

    if expected_output_pattern is not '':

        found = re.search(expected_output_pattern, actual_output)

        if not found:
            print 'Command [%s] has unexpected output: %s' % (command,
                                                              actual_output)
            return False

    return True


host = socket.gethostname()

edns_internal_validation_set = collections.OrderedDict()

edns_internal_validation_set['BIND-dig'] = {'command': 'dig @' + host + ' +short www.google.com',
                                            'timeout': 5,
                                            'expected_output_pattern': '^\d+\.\d+\.\d+\.\d+',
                                            'exit_code': 0}

print 'Beginning EDNS internal validation.'

passed = True
for service, validation_rules in edns_internal_validation_set.iteritems():
    if not Validate(validation_rules['command'],
                    validation_rules['timeout'],
                    validation_rules['expected_output_pattern'],
                    validation_rules['exit_code']):
        print '%s validation : FAIL' % service
        passed = False
        break
    print '%s validation: PASS' % service

if passed:
    print 'EDNS internal validation : PASS'
    sys.exit(0)
else:
    print 'EDNS internal validation : FAIL'
    sys.exit(1)
