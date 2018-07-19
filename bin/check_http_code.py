#!/opt/sfdc/python27/bin/python

# imports
import requests
import re
from argparse import ArgumentParser, RawTextHelpFormatter
import logging
import sys
from socket import gethostname, socket, AF_INET, SOCK_STREAM
try:
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
except ImportError as error:
    logging.error(error)


# Function to get the site domain
def host_domain():
    return gethostname().split('.')[1]


class CheckRemoteUrl(object):
    """
    This class is used to validate non http port open on remote hosts.
    """

    def __init__(self):
        self.domain = host_domain()
        self.err_dict = {}

    def socket_based_port_check(self, hostname, port):
        """
        :param hostname:  This Function will take Hostname as Argument
        :param port: This Function will take Port as an argument along with hostname
        :return: 0 == Successfull or 1 == Unsuccessfull
        """
        sock = socket(AF_INET, SOCK_STREAM)
        port = int(port)
        result = sock.connect_ex((hostname, port))
        if result == 0:
            print("{} - Port is open for {}".format(port, hostname))
            return 0
        else:
            print("{} - Port is not open for {}".format(port, hostname))
            return 1

    @staticmethod
    def requests_retry_session(retries=3, backoff_factor=3.0, status_forcelist=(500, 502, 504), session=None):
        """
        This function will retry(3) on remote API.

        :param retries: Total number of retries to allow.
        :param backoff_factor: A backoff factor to apply between attempts after the second try
        :param status_forcelist: A set of integer HTTP status codes that we should force a retry on.
        :param session:
        :return:
        """
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        return session

    # Class method to build the url from given hostname and port
    def build_url(self, hostname, port):
        """
        :param hostname: This function will take hostname as argument
        :param port: API exposed on port
        :return: url
        """
        url = None
        if re.search(r'argusws', hostname):
            url = "http://{0}.{1}.sfdc.net:{2}/argusws/help" .format(hostname, self.domain, port)
        elif re.search(r'argusui', hostname):
            url = "http://{0}.{1}.sfdc.net:{2}/argus" .format(hostname, self.domain, port)
        # Added to check Argus WriteD web based service validation
        elif re.search(r'argustsdbw', hostname):
            url = "http://{0}.{1}.sfdc.net:{2}" .format(hostname, self.domain, port)
        # End
        # Added to check Argus Readd service validation
        elif re.search(r'argustsdbr', hostname):
            url = "http://argus-tsdb.data.sfdc.net:{0}" .format(port)
        # End
        # Added to check remote port for ACS hosts - T-1780845
        elif re.search(r'acs', hostname):
            url = "http://{0}.{1}.sfdc.net:{2}/apicursorfile/v/node/status".format(hostname, self.domain, port)
        # Added to check Health url on synthetics_agent
        elif re.search(r'syntheticsagent|syntheticsmaster', hostname):
            if port == "8086":  # Hack to hit specific endPoint
                url = "http://{0}.{1}.sfdc.net:{2}/synthtx/main".format(hostname, self.domain, port)
            else:
                url = "http://{0}.{1}.sfdc.net:{2}/health".format(hostname, self.domain, port)
        logging.debug("Built url {0}" .format(url))
        # print("Port is open for {}".format(hostname))
        return url

    # Class method to check the return code from remote url
    def check_return_code(self, url):
        """
        :param url: This method will take url built from other method and check the response code
        :return: None
        """
        try:
            logging.debug("Connecting to url {0}" .format(url))
            try:
                s = requests.Session()
                ret = self.requests_retry_session(session=s).get(url)
            except (ImportError, AttributeError) as err:
                print("Import error {0}, ignoring retry...".format(err))
                ret = requests.get(url, allow_redirects=True)
            if ret.status_code != 200:
                print("Could not connect to remote url {0} ".format(url))
                self.err_dict[url] = "ERROR"
            else:
                print("Received 200 OK from remote url {0} " .format(url))
        except requests.ConnectionError as e:
            print("Couldn't connect to port {0} on remote url {1}" .format(port, url))
            self.err_dict[url] = "ERROR"

    @staticmethod
    # Function to control the exit status
    def exit_status():
        """
        Function to give control to user to exit with status 1 OR 0 in case of any issue
        :return: 
        """
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
    """
    Main function to call above class method based on http OR non http based port validation
    :return: None
    """
    obj = CheckRemoteUrl()
    # Added/Modified To validate Argus Metrics|Alert|MQ JMX/JAVA based Port using Sockets.
    for host in hosts:
        if re.search(r'argusmetrics|argusalert|argusmq|arguscache|argusannotation|argusajna|stgmgt|stgpm|-cs|lapp'
                     r'|searchidx|searchmgr', host):
            failed_connect = False
            for port in ports:
                status = obj.socket_based_port_check(host, port)
                if status != 0:
                    failed_connect = True
            if failed_connect:
                obj.exit_status()
        else:
            for port in ports:
                ret_url = obj.build_url(host, port)
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
    ports = args.port.split(',')
    if len(ports) == 1:
        port = ports[0]
    main()
