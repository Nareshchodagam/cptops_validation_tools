#!/usr/bin/env python

# Script to be run on a Momentum MTA, to send mail on each binding. It
# then checks the logs to make sure all the mail delivered. 
#
# You should be able to run it with no options. Pass -h for help.


import sys
import argparse
import smtplib
import os
import time
import re

bindings = (
    'bounce-1',
    'system-1',
    'service-1',
    'org-direct-a-1-1',
    'org-direct-a-2-1',
    'org-direct-a-3-1',
    'org-direct-b-1-1',
    'org-direct-b-1-2',
    'org-direct-b-1-3',
    'org-direct-b-1-4',
    'org-direct-b-2-1',
    'org-direct-b-2-2',
    'org-direct-b-3-1',
    'org-direct-b-3-2',
    'org-direct-b-3-3',
    'org-direct-b-3-4',
    'org-direct-c-1-1',
    'org-direct-c-2-1',
    'org-direct-c-3-1',
    'gack-1',
    'org-relay-1'
)

logfile = '/var/log/ecelerity/sfdclog.ec'
pid = os.getpid()

def perform_test(settings):
    
    # We are going to be searching the logs for the new messages we
    # send. If we record the current log size, we can avoid searching
    # too far back
    logsize = os.path.getsize(logfile)

    send_messages(settings)
    return wait_for_logs(settings, logsize, pid)

def send_messages(settings):
    smtp = smtplib.SMTP("internal")
    smtp.set_debuglevel(settings.verbose)
    for binding in bindings:
        send_message_to_binding(smtp, settings, binding)
        if settings.delay > 0:
            time.sleep(settings.delay)

def send_message_to_binding(smtp, settings, binding):
    messageid="<%s-%s@testallbindings.py>" % (pid, binding)
    body = """From: %s\r
To: %s\r
Message-ID: %s\r
Subject: testing binding %s
X-SFDC-Binding: %s
X-SFDC-Test-Binding: None

Testing binding %s.\r
""" % (settings.sender, settings.recipient, messageid, binding, binding, binding)
    
    smtp.sendmail(settings.sender, [settings.recipient], body)
    
def wait_for_logs(settings, log_offset, identifier):
    # Check for all of the messages to show up as delivered in the logs
    bindings_to_find = set(bindings)
    end_time = time.time() + settings.wait
    pattern = re.compile('@([PD])@%s@.*@<%s-([^@]+)@testallbindings.py>' % (settings.recipient, identifier))

    # Loop until we've found them all or time expires
    while bindings_to_find and time.time() < end_time:
        with open(logfile, 'r') as logs:

            # Skip what we've already seen
            logs.seek(log_offset)

            for line in logs:
                match = pattern.search(line)
                if match:
                    event = match.group(1)
                    found = match.group(2)
                    if found in bindings_to_find:
                        if event == "P":
                            print("Permanent delivery failure for %s" % found)
                        bindings_to_find.remove(found)
                        sys.stdout.write('.')
                        if not bindings_to_find:
                            break
                # update the offset so next time we start searching at
                # the beginning of the last line we've seen (in case
                # we catch half a line)
                log_offset = max(logs.tell() - len(line), log_offset)
        time.sleep(1)

    print

    if bindings_to_find:
        print('The following bindings were not delivered:')
        for binding in bindings_to_find:
            print(binding)
        return 1
    else:
        print("All messages were successfully delivered to %s" % settings.recipient)
	return 0


##########################################################################
# Command Line                                                           #
##########################################################################

def process_command_line(argv):
    """
    Return a 2-tuple: (settings object, args list).
    `argv` is a list of arguments, or `None` for ``sys.argv[1:]``.
    """

    default_address = "emailreleaseverification@salesforce.com"

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--to', help='To (recipient) address', dest='recipient', action='store', default=default_address)
    parser.add_argument('-f', '--from', help='From (sender) address', dest='sender', action='store')
    parser.add_argument('-d', '--delay', help='Delay (seconds) between sending messages', dest='delay', type=int, 
                        action='store', default=0)
    parser.add_argument('-w', '--wait', help='Time (seconds) to wait for log messages. Default 120.', dest='wait', type=int, 
                        action='store', default=120)
    parser.add_argument('-v', '--verbose', help='Print debug info', dest='verbose', action='store_true', default=False)

    settings = parser.parse_args()

    if settings.sender is None:
        settings.sender = settings.recipient

    return settings

def main():
    settings = process_command_line(sys.argv)
    return perform_test(settings)

if __name__ == '__main__':
    status = main()
    sys.exit(status)
