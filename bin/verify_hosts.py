#!/usr/bin/env python
'''
    Title -
    Author - CPT - cptops@salesforce.com
    Status - Active
    Created - 10-03-2016
'''

# revrting dummy_commit - 27/05
# Adding Dummy commit 
# modules
from __future__ import print_function
import sys, os

if "/opt/sfdc/python27/lib/python2.7/site-packages" in sys.path:
    sys.path.remove("/opt/sfdc/python27/lib/python2.7/site-packages")
try:
    import pexpect
except:
    print("ERROR: pexpect module not found/installed")
    sys.exit(1)
import socket
from argparse import ArgumentParser
import logging, shlex, json, time
from multiprocessing import Process, Queue
from subprocess import Popen, PIPE
from StringIO import StringIO
import unicodedata, re
from os import path, environ
import getpass, ConfigParser
from datetime import datetime

sys.path.append('/opt/cpt/')
from GUS.base import Auth
from GUS.base import Gus

CONFIGDIR = environ['HOME'] + "/.cptops/config"
config = ConfigParser.ConfigParser()
hostname = socket.gethostname()
user_name = os.environ.get('USER')

if re.search(r'(sfdc.net)', hostname):
    sys.path.append("/opt/cpt/km")
    from katzmeow import get_creds_from_km_pipe
    try:
        import synnerUtil
    except ImportError:
        logging.error("Error: synnerUtil.py is not found under /opt/cpt/bin/. Try updating cpt-tools or get the file from CPT's codebase")
        sys.exit(1)

class SynnerError(Exception):
    pass

class GusError(Exception):
    pass

class AuthError(Exception):
    pass

class HostsCheck(object):
    """
    :param: Class definition which accepts bundle name and case_no as command line arguments and pass to class methods.
    """

    def __init__(self, case_no, bundle=None, osce6=None, osce7=None, force=False):
        self.bundle = bundle
        self.case_no = case_no
        self.data = []
        self.user_home = path.expanduser('~')
        self.force = force
        self.osce6 = osce6
        self.osce7 = osce7

    def otp_gen(self):
        syn = synnerUtil.Synner()
        retry_count = 3
        otp = str(syn.get_otp())
        count = 0
        while not otp.startswith("ddd"):
            if count == retry_count:
                print("Retrying...")
                raise SynnerError
                break
            otp = str(syn.get_otp())
            count += 1
        return otp

    def exec_cmd(self, host, kpass, otp, cmd1, cmd2):
        output = ""
        child = pexpect.spawn(cmd1, timeout=10)
        prompt = child.expect([pexpect.TIMEOUT, "[Pp]assword:", pexpect.EOF])
        if prompt == 2:
            raise AuthError
        elif prompt == 1:
            child.sendline(kpass)
        if (child.expect([pexpect.TIMEOUT, "Please provide YubiKey OTP.*", pexpect.EOF], timeout=10)) == 1:
            if not otp:
                raise GusError
            else:
                child.sendline(otp)
        if (child.expect([pexpect.TIMEOUT, "[Pp]assword:", "Please provide YubiKey OTP.*", pexpect.EOF], timeout=10) in [1,2]):
            raise AuthError
        child.sendline(cmd2)
        child.expect([pexpect.TIMEOUT, ".*]$.*", pexpect.EOF], timeout=6)
        output = str(child.before)
        child.close()
        return output

    def check_host(self, host, passwd, otp, p_queue, session, gus_conn, migration):
        """
            This function takes a host and check if host is alive and patched/not-patched
            if migration is true, it'll check whether the host is on CE6 or not. 
            :param: Accept hostname
            :return: Returns a dict with key as hostname and value host_status(Down, patched, no-patched)
            :rtype: dict
        """
        host_dict = {}
        socket_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        orbFile = "/opt/cpt/remote/orb-check.py"
        try:
            fh = open(orbFile, 'r')
        except IOError:
            print("Ensure presence of path: " + orbFile)
        rc = None

        lh_details = gus_conn.get_logical_host_id(session, host)
        try:
            host_id = lh_details['records'][0]['Id']
            os_version = lh_details['records'][0]['Major_OS_Version__c']
            logging.debug("Logical Host {0} Id is {1} ".format(host, host_id))
        except IndexError:
            logging.error("Error occured while fetching details for host {0}".format(host))
            host_dict[host] = "LHNotFound"
            p_queue.put(host_dict)
            return

        rma = self.check_host_open_rma(session, gus_conn, host)
        if rma:
            logging.info("Host {} has open RMA - {}".format(host, rma))
            host_dict[host] = "RMA #{}".format(rma)
            self.update_patching_lh(session, gus_conn, host, host_id, "HostRMA.{}".format(rma))
            logging.error(host_dict)
            p_queue.put(host_dict)
            return
            
        try:
            if host:
                socket_conn.settimeout(10)
                socket_conn.connect((host, 22))
                if migration:
                    osCheckCmd = "cat /etc/centos-release"
                    osCmd = "ssh -o StrictHostKeyChecking=no  {0}".format(host)
                    output = self.exec_cmd(host, passwd, otp, osCmd, osCheckCmd)
                    console_out = output.lower()
                    os = console_out.find("centos release 6")
                    if os != -1:
                        host_dict[host] = "Centos6"
                    else:
                        host_dict[host] = "NotCentos6"
                else:
                    if not self.bundle:
                        bundle_to_pass = (self.osce6 if int(os_version) == 6 else self.osce7)
                    else:
                        bundle_to_pass = self.bundle
                    orbCheckCmd = "python /usr/local/libexec/orb-check.py -v {0}".format(bundle_to_pass)
                    orbCmd = "ssh -o StrictHostKeyChecking=no  {0}".format(host)
                    output = self.exec_cmd(host, passwd, otp, orbCmd, orbCheckCmd)
                    console_out = output.lower() # hack for fool-proof orb-check
                    if ("does not match" in console_out or "reboot required" in console_out or "action required" in console_out):
                        rc = True
                        flag = False
                    elif ("unrecognized arguments" in console_out or "valueerror" in console_out or "error: argument" in console_out):
                        rc = True
                        flag = True
                    elif ("no such file or directory" in console_out):
                        rc = False
                        flag = True
                    else:
                        rc = False
                        flag = False
                    if not rc:
                        if flag:
                            host_dict[host] = "ORBCheckMissing"
                            print("orb-check.py is missing on {0}. Run puppet manually.".format(host))
                        else:
                            host_dict[host] = "patched"
                            print("{0} - already patched".format(host))
                    else:
                        if flag:
                            print("Unable to determine the patch bundle on {0} due to old version of orb-check.py. Adding to include file anyway.".format(host))
                        host_dict[host] = "no_patched"
        except pexpect.EOF:
            host_dict[host] = "PexpectError"
            print("ERROR: {0} reached pexpect EOF".format(host))
        except pexpect.TIMEOUT:
            host_dict[host] = "PexpectError"
            print("ERROR: {0} reached pexpect TIMEOUT".format(host))
        except SynnerError:
            self.update_patching_lh(session, gus_conn, host, host_id, "AuthIssue.SSH")
            host_dict[host] = "SynnerError"
            print("ERROR: {0} Waiting at password/OTP prompt. Either previous password or OTP were not accepted. Please try again.".format(host))
        except GusError:
            host_dict[host] = "GusNotUpdated"
            print("ERROR: GUS has stale data about {0}. Host is expecting YubiKey OTP whereas GUS says otherwise.".format(host))
        except AuthError:
            self.update_patching_lh(session, gus_conn, host, host_id, "AuthIssue.Kerberos")
            host_dict[host] = "AuthError"
            print("ERROR: Unable to authenticate to host {0}.".format(host))
        except socket.error as error:
            self.update_patching_lh(session, gus_conn, host, host_id, "HostDown.PrePatch")
            host_dict[host] = "Down"
            print("{0} - Error on connect: {1}".format(host, error))
            socket_conn.close()
        except Exception as e:
            print("Unexpected error occured: " + str(e))
            exit(1)
        logging.debug(host_dict)
        p_queue.put(host_dict)

    def check_host_open_rma(self, session, gus_conn, host):
        # RMA GUS Record Type - 012B000000009fDIAQ
        query = "SELECT Case_Record__c FROM SM_Case_Asset_Connector__c WHERE Case_RecordType__c = '012B000000009fD' AND Host_Name__c = '{}'".format(host)
        result = gus_conn.run_query(query, session)
        rma = None
        for data in result['records']:
            rma_case_id = str(data['Case_Record__c'])
            q = "SELECT CaseNumber FROM Case WHERE (Id = '{}')  AND (Status != 'Closed' AND Status != 'Closed - Duplicate' AND Status != 'Closed - Not Executed' AND Status != 'New' AND Status != 'Return to Service')".format(rma_case_id)
            res = gus_conn.run_query(q, session)
            if len(res['records']) > 0:
                for d in res['records']:
                    rma = d['CaseNumber']
        return rma

    def update_patching_lh(self, session, gus_conn, host, host_id, patch_issue):
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y")
        patch_issue_full = "{};{}".format(str(dt_string), patch_issue)

        payload = {
            'Patch_Issue__c': patch_issue_full
        }
        ret = gus_conn.update_patching_lh(session, payload, host_id)
        if ret.status_code == 204:
            logging.info("Updated GUS Logical_host field for host {0} ".format(host))
        else:
            logging.error("Update to GUS failed for host {0} ".format(host))

    def write_to_file(self):
        """
        This function is to write files based on host_status.
        :param case_no: This is case number used to generate files prefix with case_no
        :param data: This is dictionary contains host as key and host_status as value
        :return: None
        """
        ex_buffer = StringIO()
        in_buffer = StringIO()
        for host_dict in self.data:
            for k, v in host_dict.items():
                if v in ('no_patched', 'Centos6'):
                    in_buffer.write("{0}".format(k) + ',')
                    logging.debug(in_buffer.getvalue())
                else:
                    if self.force and v in ('patched', 'NotCentos6'):
                        in_buffer.write("{0}".format(k) + ',')
                        logging.debug(in_buffer.getvalue())
                    ex_buffer.write(
                        "{0} -  {1}".format(k, host_dict[k]) + '\n')
                    logging.debug(ex_buffer.getvalue())
        in_hosts = in_buffer.buf.rstrip(',')
        with open(self.user_home + '/' + self.case_no + '_exclude', 'a+') as ex_file:
            ex_file.write(ex_buffer.getvalue())
        with open(self.user_home + '/' + self.case_no + '_include', 'w') as in_file:
            in_file.write(in_hosts)

    def check_file_empty(self):
        """
        This function is used to check if the case_no_include file is empty.
        If file is empty the program will exit with status 1.
        :return: None
        """
        filename = "{0}/{1}_include".format(self.user_home, self.case_no)
        if path.getsize(filename) == 0:
            raise SystemExit("File {0} is empty, so quitting".format(filename))

    def process(self, hosts, mfa_hosts, kpass, session, gus_conn, migration):
        """
        This function will accept hostlist as input and call check_host function and store value in
        shared memory(Queue).
        :param hosts: A list of hosts
        :return: None
        """
        process_q = Queue()
        p_list = []
        syn = synnerUtil.Synner()
        for host in hosts:
            if host in mfa_hosts:
                try:
                    otp = self.otp_gen()
                except Exception:
                    print("Error: Hostlist contains MFA hosts. Synner is not fully functional in this DC. Exiting.")
                    sys.exit(1)
                except SynnerError:
                    print("Error: Something went wrong with Synner.")
                    sys.exit(1)
            else:
                otp = False
            process_inst = Process(target=self.check_host, args=(host, kpass, otp, process_q, session, gus_conn, migration))
            p_list.append(process_inst)
            process_inst.start()
            time.sleep(1)
        for pick_process in p_list:
            pick_process.join()
            self.data.append(process_q.get())

def mfa_check(session, host_list, gus_conn):
    """
    :param session: GUS session dict
    :type session: dict
    :param host: Hostname to query
    :type host: str
    :param gus_conn: GUS Class Object
    :return: Tuple of results
    :rtype: tuple
    """
    # host_tuple = "('" + "','".join(host_list) + "')"
    mfa_hosts = []
    if len(host_list) == 1:
        hosts = str("('"+host_list[0]+"')")
    else:
        hosts = tuple(host_list)
    query = "SELECT Host_Name__c,Authentication_Method__c FROM SM_Logical_Host__c WHERE Host_Name__c in {}".format(hosts)
    result = gus_conn.run_query(query, session)
    for data in result['records']:
        auth_method = str(data['Authentication_Method__c']).lower()
        if ('mfa' in auth_method):
            mfa_hosts.append(data['Host_Name__c'])
    logging.debug("mfa_hosts {}".format(mfa_hosts))
    return mfa_hosts

def find_proxy(hostname):
    """
    This function is to find proxy for internal DCs <W-3758595>
    :param hostname: hostname
    :type hostname: str
    :return: Nothing
    :rtype: None
    """
    site = hostname.split('.')[0].split('-')[3]
    if re.search(r'rz1|crz|crd|chx|wax', site, re.IGNORECASE):
        environ['https_proxy'] = "http://public-proxy1-0-{0}.data.sfdc.net:8080/".format(site)
    else:
        environ['https_proxy'] = "http://public0-proxy1-0-{0}.data.sfdc.net:8080/".format(site)
    logging.debug("https_proxy env variable is set to {0}".format(environ.get("https_proxy", "")))
    # logger.debug("setup proxy %s" .format(environ['https_proxy']))

def main():
    """
    This is main function which will accept the command line argument and pass to the class methods.
    :return:
    """
    parser = ArgumentParser(description="""To check if remote hosts are accessible over SSH and are not patched""",
                            usage='%(prog)s -H <host_list> --bundle <bundle_name> --case <case_no>',
                            epilog='python verify_hosts.py -H cs12-search41-1-phx --bundle 2016.09 --case 0012345')
    parser.add_argument("-M", dest="migration", help="To get the Centos6 hosts only", action="store_true")
    parser.add_argument("--bundle", dest="bundle", help="Bundle name")
    parser.add_argument("-H", dest="hosts", required=True, help="The hosts in command line argument")
    parser.add_argument("--case", dest="case", required=True, help="Case number")
    parser.add_argument("--force", dest="force", action="store_true", help="Case number")
    parser.add_argument("-v", dest="verbose", help="For debugging purpose", action="store_true")
    parser.add_argument("--encrypted_creds", dest="encrypted_creds", help="Pass creds in via encrypted named pipe")
    parser.add_argument("--decrypt_key", dest="decrypt_key", help="Used with --encrypted_creds description")
    parser.add_argument("--osce6", dest="osce6", help="The bundle name for CE6")
    parser.add_argument("--osce7", dest="osce7", help="The bundle name for CE7")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if args.encrypted_creds:
        try:
            kpass, username, gpass = get_creds_from_km_pipe(pipe_file=args.encrypted_creds, decrypt_key_file=args.decrypt_key)
            username = username.split('@')[0]
        except ImportError as e:
            print("Import failed from GUS module, %s" % e)
            sys.exit(1)
    else :
        kpass = getpass.getpass("Enter your kerberos password: ")
        gpass = getpass.getpass("Enter your GUS password: ")
    
    try:
        config.readfp(open(CONFIGDIR + '/creds.config'))
    except IOError:
        logging.error("No creds.config file found")
        exit(1)
    try:
        username = config.get('GUS', 'username')
        client_id = config.get('GUS', 'client_id')
        client_secret = config.get('GUS', 'client_secret')
    except ConfigParser.Error:
        logging.error('Problem getting username, client_id or client_secret')
        exit(1)

    find_proxy(hostname)
    gus_conn = Gus()
    auth_obj = Auth(username, gpass, client_id, client_secret)
    session = auth_obj.login()
    hosts = args.hosts.split(',')
    mfa_hosts = mfa_check(session, hosts, gus_conn)

    if args.bundle:
        bundle = args.bundle
    else:
        bundle = "current"
    hosts = args.hosts.split(',')
    case_no = args.case
    force = args.force
    if args.bundle:
        class_object = HostsCheck(case_no, bundle=bundle, osce6=None, osce7=None, force=force)
    else:
        class_object = HostsCheck(case_no, bundle=None, osce6=args.osce6, osce7=args.osce7, force=force)
    migration = True if args.migration else False
    hosts = args.hosts.split(',')
    class_object.process(hosts, mfa_hosts, kpass, session, gus_conn, migration)
    class_object.write_to_file()
    class_object.check_file_empty()


if __name__ == "__main__":
    main()
