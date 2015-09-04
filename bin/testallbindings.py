#!/usr/bin/python
import logging
import os
from optparse import OptionParser

ec_path='/opt/msys/ecelerity/bin/ec_sendmail'

bindings=[
    'bounce-1',
    'site-relay-1',
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
    ]

if __name__ == "__main__":

    usage="""

    %prog
    ------------------------------------------------------------------------

    # Execute test
    %prog -e emailreleaseverification@salesforce.com

    ------------------------------------------------------------------------

    """

    parser = OptionParser(usage)
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help="Verbosity")
    parser.add_option("-e", dest="email_dest", help="Email address to spam")
    (options, args) = parser.parse_args()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    for binding in bindings:
        content = "Testing binding: " + binding

        message = """
        From: MTA Patching Validator <%(sender)s>
        To: MTA Validation Team <%(email_dest)s>
        Subject: SMTP e-mail test
        X-SFDC-Binding: %(binding)s
        X-SFDC-Test-Binding: None

        %(content)s
EOF
        """ % {'binding':binding,
               'email_dest':options.email_dest,
               'content':content,
               'sender':'mta_validation@salesforce.com'}


        cmd=ec_path + " " + options.email_dest + "  <<EOF " + message
        
        logging.debug(cmd)

        try:
            os.system(cmd)
            print('Sent mail for ' + binding)
        except:
            print('Unable to send mail')
