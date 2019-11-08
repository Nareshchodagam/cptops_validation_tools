#!/usr/bin/env python
"""Functions for interactions with Synner."""

import sys
if "/opt/sfdc/python27/lib/python2.7/site-packages" in sys.path:
   sys.path.remove("/opt/sfdc/python27/lib/python2.7/site-packages")
import pexpect

class Synner:

   def get_otp(self):
      count = 3
      cmd = "/opt/synner/synner -action generate"
      try:
         otp = pexpect.spawn(cmd)
         otp.expect("ddd.*")
         return otp.after
      except:
         print("ERROR: OTP %s" % str(otp.before))
         sys.exit(1)
