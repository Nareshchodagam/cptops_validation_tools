#!/usr/bin/python
import re
import subprocess


def get_rpm_details():
    rpm_vers = ''
    output = []
    proc = subprocess.Popen(['rpm', '-qa'])
    print(proc)

    #for i in rpm_vers.splitlines():
    #        if re.search(r'nscd|glibc',i):
    #                output.append(i)
    #results = check_rpm_vers(output)
    #return results


def check_rpm_vers(input):
    output = { 'nscd': 0, 'glibc': 0, 'glibc-common': 0,
                    'glibc-utils': 0, 'glibc-i686': 0 }
    for i in input:
        if re.search(r'nscd-2.12-1.149.el6_6.5.x86_64', i):
            output['nscd'] = 1
        if re.search(r'glibc-2.12-1.149.el6_6.5.x86_64', i):
            output['glibc'] = 1
        if re.search(r'glibc-2.12-1.149.el6_6.5.i686', i):
            output['glibc-i686'] = 1
        if re.search(r'glibc-utils-2.12-1.149.el6_6.5.x86_64', i):
            output['glibc-utils'] = 1
        if re.search(r'glibc-common-2.12-1.149.el6_6.5.x86_64', i):
            output['glibc-common'] = 1
    return output

if __name__ == "__main__":
    get_rpm_details()
