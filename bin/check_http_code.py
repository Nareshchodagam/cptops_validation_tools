#!/usr/bin/env python

# imports
import requests
import re
from argparse import ArgumentParser, RawTextHelpFormatter
import logging
import sys
from socket import gethostname

# Function to get the site domain

def host_domain():
    return gethostname().split('.')[1]


class CheckRemoteUrl(object):

    def __init__(self):
        self.domain = host_domain()
        self.err_dict = {}

    # Class method to build the url from given hostname and port
    def build_url(self, hostname):
        """
        :param hostname: This function will take hostname as argument
        :return: url
        """
        url = None
        if re.search(r'argusws', hostname):
            url = "http://{0}.{1}.sfdc.net:{2}/argusws/help" .format(hostname, self.domain, port)
            logging.debug("Built url {0}" .format(url))
        return url

    # Class method to check the return code from remote url
    def check_return_code(self, url):
        """
        :param url: This method will take url built from other method and check the response code
        :return: None
        """
        try:
            logging.debug("Connecting to url {0}" .format(url))
            ret = requests.get(url, allow_redirects=False)
            if ret.status_code != 200:
                print("Could not connect to remote url {0}".format(url))
        except requests.ConnectionError as e:
            print("Couldn't connect to port {0} on remote url{1}" .format(port, url))
            self.err_dict[url] = "ERROR"

    # Function to control the exit status
    def exit_status(self):
        while True:
            u_input = raw_input("Do you want to exit with exit code '1' (y|n) ")
            if u_input == "y":
                sys.exit(1)
            elif u_input == "n":
                sys.exit(0)
            else:
                print("Please enter valid choice (y|n) ")
                continue

# Main function to instantiate class and class methods
def main():
    obj = CheckRemoteUrl()
    for host in hosts:
        ret_url = obj.build_url(host)
        obj.check_return_code(ret_url)
    if obj.err_dict:
        obj.exit_status()

if __name__ == "__main__":
    parser = ArgumentParser(description="""This code is to check the return code from remote API
    python check_http_code.py -H cs12-ffx41-1-phx -P 8080""", usage='%(prog)s -H <host_list>',
                            formatter_class=RawTextHelpFormatter)
    parser.add_argument("-H", dest="hosts", required=True, help="The hosts in command line argument")
    parser.add_argument("-P", dest="port", required=True, help="The hosts in command line argument")
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    hosts = args.hosts.split(',')
    port = args.port
    main()
