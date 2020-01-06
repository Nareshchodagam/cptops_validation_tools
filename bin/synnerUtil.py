#!/usr/bin/env python
"""Functions for interactions with Synner."""

import sys
if "/opt/sfdc/python27/lib/python2.7/site-packages" in sys.path:
   sys.path.remove("/opt/sfdc/python27/lib/python2.7/site-packages")

try:
   import pexpect
except:
   print("ERROR: pexpect module not found/installed")
   sys.exit(1)

class Synner:

   def get_otp(self):
      from os import path
      if not path.exists("/usr/bin/synner"):
         print("WARNING: synner is not installed under /usr/bin/synner. Any MFA-enabled hosts will not be accessible.")
         print("Returning empty otp")
         return ""
      cmd = "/opt/synner/synner -action generate"
      otp = pexpect.spawn(cmd)
      try:
         otp.expect("ddd.*")
      except Exception as e:
         print("Generating synthetic otp failed")
      return otp.after
