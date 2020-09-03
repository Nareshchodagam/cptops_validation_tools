from __future__ import print_function

""" FFX Package Validator
Purpose:        Checks FFX Package Repo Validation
Description:    This Script is used to validate if the FFX Package with Versions exist in this Script. This will be executed as part of Migration Manager Workflow by CPT team.
Email:          dbpie@salesfore.com
Author:         Vinod Egallapati
"""

import sys
import subprocess


'''
Capture the cases where Package with specified version doesn't exist in the repo
'''
missing_package_version ={}


def runCMD(cmd='ls'):
    out = ''
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    retVal = proc.wait()
    out = proc.stdout.read()
    proc.stdout.close()
    if retVal != 0:
        return False, out
    else:
        return True, out

def pre_requisites():
    if ((len(sys.argv) - 1) != 1):
        print("USAGE: Please provide 1 mandatory runtime argument to this script")
        print("Please provide FFX App@Version with comma separated.")
        print("Example: lightcycle-snapshot@lightcycle-snapshot.1.2.506,sfdc-base@226.17,mandm-agent@Agent.68.5")
        sys.exit(1)

def packageRepoValiator(app_name=None,app_version=None):
    global missing_package_version
    if app_name is not None and app_version is not None:
        cmd_status,res = runCMD('/opt/gro/releasetools/scripts/chkmf -l ^{}$ | grep {} | wc -l'.format(app_version,app_name))
        if(cmd_status):
            if int(res):
                print("Package {} with version {} exists in the repo.Check....PASSED".format(app_name,app_version))
            else:
                print("Package {} with version {} don't exist in the repo.Check....FAILED".format(app_name,app_version))
                missing_package_version.update({app_version: app_name})

def main():
   pre_requisites()
   app_with_version = sys.argv[1].strip()
   apps = app_with_version.split(",")
   for app in apps:
       app_name = app.split("@")[0]
       app_version = app.split("@")[1]
       packageRepoValiator(app_name,app_version)
   if missing_package_version:
       print("\nFew validations got FAILED.Exiting the Script...")
       exit(1)
   else:
       print("\nAll Validations got PASSED.")


if __name__ == '__main__':
    main()
