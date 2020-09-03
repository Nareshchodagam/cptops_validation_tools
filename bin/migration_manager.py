#!/usr/bin/python

from argparse import ArgumentParser
import logging
from os import path
from subprocess import call, Popen, PIPE, CalledProcessError
import sys
import threading
import Queue
import json
import re
import time
import requests
import getpass


class Util:

    def __init__(self):
        self.user_home = path.expanduser("~")

    def has_valid_kerberos_ticket(self):
        return True if call(['klist', '-s']) == 0 else False

    def check_file_exists(self, casenum, type=""):
        """
        method that checks whether the given type of file exists or not
        :type: include,exclude,cnc,hostinfo
        """
        return path.exists("%s/%s_%s" % (self.user_home, casenum, type))

    def read_hostlist_from_file(self, casenum, type=""):
        """
        method that reads the hostlist from the given type of file
        """
        file_name = "%s/%s_%s" % (self.user_home, casenum, type)

        if not self.check_file_exists(casenum, type=type):
            logger.error("%s is not found or inaccessible" % file_name)
            sys.exit(1)

        try:
            f = open(file_name, "r")
            return str(f.readline().rstrip("\n").rstrip(",")).split(",")
        except:
            logger.error("%s is not readable" % file_name)
            return

    def write_to_include_file(self, casenum, hostlist):
        """
        method that writes given hostlist to include file
        """
        file_name = "%s/%s_include" % (self.user_home, casenum)
        try:
            f = open(file_name, "w+")
            f.write(','.join(hostlist))
            f.close()
            return
        except IOError:
            logger.error("Error writing to %s" % file_name)
            sys.exit(1)

    def write_to_exclude_file(self, casenum, hostname, reason):
        """
        method that appends the given host to exclude file along with reason why it is excluded
        """
        file_name = "%s/%s_exclude" % (self.user_home, casenum)
        try:
            old_data = ""
            try:
                f = open(file_name, "r")
                old_data = f.readlines()
                f.close()
            except:
                old_data = ""
            data = ""
            for line in old_data:
                data += line
            new_line = "%s  -   %s" % (hostname, reason)
            final_data = "%s\n%s" % (data, new_line)
            f = open(file_name, "w+")
            f.write(final_data)
            f.close()
            return
        except:
            logger.error("Error writing to %s" % file_name)
            sys.exit(1)

    def write_to_hostinfo_file(self, casenum, hostinfo):
        """
        method that writes hostinfo to hostinfo file
        """
        file_name = "%s/%s_hostinfo" % (self.user_home, casenum)
        try:
            f = open(file_name, "w+")
            json.dump(hostinfo, f, indent=4)
            f.close()
            logger.info("hostinfo is dumped into %s" % file_name)
            return
        except IOError:
            logger.error("Error writing hostinfo to %s " % file_name)
            sys.exit(1)

    def write_to_cnc_file(self, casenum, hostinfo):
        """
        method that identifies hp hosts and writes respective cnc's to cnc file
        """
        file_name = "%s/%s_cnc" % (self.user_home, casenum)
        cnc_list = []
        for item in hostinfo:
            cnc_api_url = item.values()[0]["cnc_api_url"]
            if not cnc_api_url == None:
                if item.values()[0]["manufacturer"] in ["HP", "HPE"]:
                    cnc_host = cnc_api_url.split("//")[1].split(".")[0]
                    if cnc_host not in cnc_list:
                        cnc_list.append(cnc_host)
        if not len(cnc_list) > 0:
            dummy = hostinfo[0].values()[0]["cnc_api_url"].split("//")[1].split(".")[0]
            cnc_list.append(dummy)
        try:
            f = open(file_name, "w+")
            f.write(','.join(cnc_list).rstrip(","))
            f.close()
            return
        except IOError:
            logger.error("Error writing HP CNC hosts info to %s" % file_name)
            sys.exit(1)


class ThreadCncInfo(threading.Thread):

    def __init__(self, queue, casenum, hosts_processed):
        threading.Thread.__init__(self)
        self.queue = queue
        self.casenum = casenum
        self.hosts_processed = hosts_processed
        self.mig = Migration()

    def run(self):
        h = self.queue.get()
        max_retries = 2
        count = 0
        result, status = self.mig.get_cnc_info(h, self.casenum)
        while status == "ERROR" and count != max_retries:
            logger.info(
                "%s - Retry #%s fetching host cnc information from iDB as it's failed in previous attempt" % (h, (count + 1)))
            result, status = self.mig.get_cnc_info(h, self.casenum)
            count += 1
        self.hosts_processed[h] = {"info": result, "status": status}
        self.queue.task_done()


class ThreadRouteCheck(threading.Thread):

    def __init__(self, queue, casenum, hosts_processed):
        threading.Thread.__init__(self)
        self.queue = queue
        self.casenum = casenum
        self.hosts_processed = hosts_processed
        self.mig = Migration()

    def run(self):
        h = self.queue.get()
        result, status = self.mig.route_check(h, self.casenum)
        self.hosts_processed[h] = {"info": result, "status": status}
        self.queue.task_done()


class ThreadImaging(threading.Thread):

    def __init__(self, queue, casenum, hosts_processed):
        threading.Thread.__init__(self)
        self.queue = queue
        self.casenum = casenum
        self.hosts_processed = hosts_processed
        self.mig = Migration()

    def run(self):
        host, role, preserve, disk_config, dry_run = self.queue.get()
        max_retries = 2 if not dry_run else 0
        count = 0
        if not dry_run:
            logger.info("Triggering image command on %s. Will be retrying for a maximum of %s times if failed" %
                        (host, max_retries))
        result, status = self.mig.trigger_image(
            host, self.casenum, role=role, preserve=preserve, disk_config=disk_config, no_op=dry_run)
        while status == "ERROR" and "error" in result.keys() and count != max_retries:
            logger.info(
                "Retry #%s image command on %s as it's failed in previous attempt" % (count, host))
            result, status = self.mig.trigger_image(
                host, self.casenum, role=role, preserve=preserve, disk_config=disk_config, no_op=dry_run)
            count += 1
        self.hosts_processed[host] = {"info": result, "status": status}
        self.queue.task_done()


class ThreadFailHost(threading.Thread):

    def __init__(self, queue, casenum, hosts_processed):
        threading.Thread.__init__(self)
        self.queue = queue
        self.casenum = casenum
        self.hosts_processed = hosts_processed
        self.mig = Migration()

    def run(self):
        host, dry_run = self.queue.get()
        max_retries = 2 if not dry_run else 0
        count = 0
        if not dry_run:
            logger.info("Triggering fail_host command on %s. Will be retrying for a maximum of %s times if failed" % (
                host, max_retries))
        result, status = self.mig.fail_host(host, self.casenum, no_op=dry_run)
        while status == "ERROR" and "error" in result.keys() and count != max_retries:
            logger.info(
                "Retry #%s fail_host command on %s as it's failed in previous attempt" % (count, host))
            result, status = self.mig.fail_host(host, self.casenum, no_op=dry_run)
            count += 1
        self.hosts_processed[host] = {"info": result, "status": status}
        self.queue.task_done()


class ThreadRebuilding(threading.Thread):

    def __init__(self, queue, casenum, hosts_processed):
        threading.Thread.__init__(self)
        self.queue = queue
        self.casenum = casenum
        self.hosts_processed = hosts_processed
        self.mig = Migration()

    def run(self):
        host, preserve, disk_config, dry_run = self.queue.get()
        max_retries = 2 if not dry_run else 0
        count = 0
        if not dry_run:
            logger.info("Triggering rebuild_failed_host command on %s. Will be retrying for a maximum of %s times if failed" % (
                host, max_retries))
        result, status = self.mig.rebuild_failed_host(
            host, self.casenum, preserve=preserve, disk_config=disk_config, no_op=dry_run)
        while status == "ERROR" and "error" in result.keys() and count != max_retries:
            logger.info(
                "Retry #%s rebuild_failed_host command on %s as it's failed in previous attempt" % (count, host))
            result, status = self.mig.rebuild_failed_host(
                host, self.casenum, preserve=preserve, disk_config=disk_config, no_op=dry_run)
            count += 1
        self.hosts_processed[host] = {"info": result, "status": status}
        self.queue.task_done()


class ThreadDeploy(threading.Thread):

    def __init__(self, queue, casenum, hosts_processed):
        threading.Thread.__init__(self)
        self.queue = queue
        self.casenum = casenum
        self.hosts_processed = hosts_processed
        self.mig = Migration()

    def run(self):
        host, role, cluster, superpod, preserve, dry_run = self.queue.get()
        result, status = self.mig.trigger_deploy(
            host, self.casenum, role=role, cluster=cluster, superpod=superpod, preserve=preserve, no_op=dry_run)
        self.hosts_processed[host] = {"info": result, "status": status}
        self.queue.task_done()


class ThreadEraseHostName(threading.Thread):

    def __init__(self, queue, casenum, hosts_processed):
        threading.Thread.__init__(self)
        self.queue = queue
        self.casenum = casenum
        self.hosts_processed = hosts_processed
        self.mig = Migration()

    def run(self):
        host = self.queue.get()
        result, status = self.mig.erase_hostname(host, self.casenum)
        self.hosts_processed[host] = {"info": result, "status": status}
        self.queue.task_done()


class ThreadUpdateOpsStatus(threading.Thread):

    def __init__(self, queue, casenum, hosts_processed):
        threading.Thread.__init__(self)
        self.queue = queue
        self.casenum = casenum
        self.hosts_processed = hosts_processed
        self.mig = Migration()

    def run(self):
        max_retries = 2
        count = 0
        host, idb_status = self.queue.get()
        result, status = self.mig.update_idb_status(
            host, self.casenum, idb_status=idb_status)
        while status == "ERROR" and "error" in result.keys() and count != max_retries:
            logger.info(
                "Retry #%s updateopsstatus command on %s as it's failed in previous attempt" % (count, host))
            result, status = self.mig.update_idb_status(
                host, self.casenum, idb_status=idb_status)
            count += 1
        self.hosts_processed[host] = {"info": result, "status": status}
        self.queue.task_done()


class ThreadCheckIdbStatus(threading.Thread):

    def __init__(self, queue, casenum, hosts_processed):
        threading.Thread.__init__(self)
        self.queue = queue
        self.casenum = casenum
        self.hosts_processed = hosts_processed
        self.mig = Migration()

    def run(self):
        host, idb_status = self.queue.get()
        result, status = self.mig.check_idb_status(host, self.casenum, expected_idb_status=idb_status)
        self.hosts_processed[host] = {"info": result, "status": status}
        self.queue.task_done()


class ThreadStatusCheck(threading.Thread):

    def __init__(self, queue, casenum, hosts_processed):
        threading.Thread.__init__(self)
        self.queue = queue
        self.casenum = casenum
        self.hosts_processed = hosts_processed
        self.mig = Migration()

    def run(self):
        host, delay, prev_cmd = self.queue.get()
        result, status = self.mig.check_status(
            host, self.casenum, delay, prev_cmd)
        self.hosts_processed[host] = {"info": result, "status": status}
        self.queue.task_done()


class ThreadDiskConfigCheck(threading.Thread):

    def __init__(self, queue, casenum, hosts_processed, validate_disk_config):
        threading.Thread.__init__(self)
        self.queue = queue
        self.casenum = casenum
        self.hosts_processed = hosts_processed
        self.validate_disk_config = validate_disk_config
        self.mig = Migration()

    def run(self):
        h = self.queue.get()
        result, status = self.mig.validate_disk_config(h, self.casenum, self.validate_disk_config)
        self.hosts_processed[h] = {"info": result, "status": status}
        self.queue.task_done()


class ThreadValidateNic(threading.Thread):

    def __init__(self, queue, casenum, hosts_processed, mac_info):
        threading.Thread.__init__(self)
        self.queue = queue
        self.casenum = casenum
        self.hosts_processed = hosts_processed
        self.mac_info = mac_info
        self.mig = Migration()

    def run(self):
        host = self.queue.get()
        result, status = self.mig.validate_nic(host, self.casenum, self.mac_info)
        self.hosts_processed[host] = {"info": result, "status": status}
        self.queue.task_done()


class Migration:

    def __init__(self):
        self.user_home = path.expanduser("~")
        self._load_role_disk_data_mapping()
        self.current_user = str(getpass.getuser()).lower()
        self.mtls_props = self._get_certs(self.current_user)

    def _get_certs(self, username):
        cert_path = "/etc/pki_service/%s/%s/certificates/%s.pem" % (username, username, username)
        key_path = "/etc/pki_service/%s/%s/keys/%s-key.pem" % (username, username, username)
        ca_path = "/etc/pki_service/ca/cacerts.pem"
        if (path.exists(cert_path) and path.exists(key_path) and path.exists(ca_path)):
            return {"capath": ca_path, "cert": cert_path, "key": key_path}
        return {"capath": None, "cert": None, "key": None}

    def _validate_certs(self, certs_data):
        if (certs_data["capath"] != None and certs_data["cert"] != None and certs_data["key"] != None):
            return True
        return False

    def _load_role_disk_data_mapping(self):
        """
        method that reads /opt/cpt/bin/role_disk_config_mapping.json and loads the configs for critical roles
        """
        config_file_path = "/opt/cpt/bin/role_disk_config_mapping.json"
        try:
            f = open(config_file_path, "r")
            self.role_disk_data_mapping = json.load(f)
        except IOError:
            logger.error("%s is not found or inaccessible" % config_file_path)
            sys.exit(1)

    def _read_host_props(self, casenum, hostname):
        """
        method that reads the hostinfo file and return given host properties
        """
        output = {}
        found = False
        host_info_file = "%s/%s_hostinfo" % (self.user_home, casenum)
        try:
            f = open(host_info_file, "r")
            host_info_dict = json.load(f)
            for item in host_info_dict:
                if hostname in item.keys():
                    output.update({"cnc_api_url": item.values()[0]["cnc_api_url"]})
                    output.update({"serial_number": item.values()[0]["serial_number"]})
                    output.update({"device_role": item.values()[0]["device_role"]})
                    output.update({"rack_position": item.values()[0]["rack_position"]})
                    output.update({"network_domain": item.values()[0]["network_domain"]})
                    output.update({"manufacturer": item.values()[0]["manufacturer"]})
                    found = True
                    break
        except IOError:
            logger.error("%s is not found or inaccessible" % host_info_file)
            found = False
        except Exception:
            logger.error("An error occured while reading %s" % host_info_file)
            found = False

        return found, output

    def _validate_role_props(self, hostname, role, disk_config, preserve, host_props, command=""):
        """
        method that validates role specific preferences for critical roles to prevent human errors
        """
        defined_disk_config = ""
        defined_data_preserve = ""
        configs = self.role_disk_data_mapping
        role_to_validate = ""

        if role == None:
            if command != "rebuild":
                logger.info("No role passed via --role for %s. Checking hostinfo" % hostname)
            if host_props["device_role"] == None or host_props["device_role"] == "":
                logger.error("Neither iDB role is present in hostinfo nor passed via --role for %s." % hostname)
                return False
            else:
                role_to_validate = host_props["device_role"]
        else:
            if host_props["device_role"] == None or host_props["device_role"] == "":
                logger.warning(
                    "We don't have iDB role in hostinfo for %s. Sticking with %s passed via --role." % (hostname, role))
                role_to_validate = role
            else:
                if role != host_props["device_role"] and command != "rebuild":
                    logger.error("%s - Passed role name doesn't match with role name fetched from iDB. '%s' <> '%s'" %
                                 (hostname, role, host_props["device_role"]))
                    return False
                else:
                    role_to_validate = role
        if role_to_validate in configs.keys():
            defined_disk_config = configs[role_to_validate]["diskConfig"]
            defined_data_preserve = configs[role_to_validate]["dataPreserve"]
            if role_to_validate in ["dnds", "mnds"]:
                filters = configs[role_to_validate]["filters"]
                for f in filters:
                    pattern = f["pattern"]
                    matched = re.match(pattern, hostname)
                    if matched != None:
                        defined_disk_config = f["diskConfig"]
                        defined_data_preserve = f["dataPreserve"]
                        break
            mismatch = False
            if command != "deploy" and disk_config != defined_disk_config:
                logger.error("%s is not supposed to be reimaged with %s disk configuration. Role %s - '%s' <> '%s'" %
                             (hostname, disk_config, role_to_validate, defined_disk_config, disk_config))
                mismatch = True
            if preserve != defined_data_preserve:
                logger.error("%s - given data preservation criteria doesn't match. Role %s - Preserve '%s' <> '%s'" %
                             (hostname, role_to_validate, defined_data_preserve, preserve))
                mismatch = True
            if mismatch:
                return False
            logger.info("%s - Role: %s, Disk Config: %s, Data Preserve: %s" %
                        (hostname, role_to_validate, disk_config, preserve))
            return True
        else:
            return True

    def exec_cmd(self, cmd):
        try:
            logger.debug("executing " + cmd)
            command = Popen([cmd], stdout=PIPE, shell=True)
            (output, err) = command.communicate()
        except CalledProcessError as e:
            logger.error(e)
            sys.exit(1)
        return output

    def get_cnc_info(self, hostname, casenum):
        """
        For a given host this method queries iDB and fetches serialNumber, apiUrl, rackUPos, manufacturer
        """
        output = {}
        status = "SUCCESS"
        try:
            ci_dict = json.loads(self.exec_cmd(
                "inventory-action.pl -q -use_krb_auth -resource hostconfig -action read -host.name " + hostname + " -fields key,value -key apiUrl"))
            sn_dict = json.loads(self.exec_cmd(
                "inventory-action.pl -q -use_krb_auth -resource host -action read -name " + hostname + " -fields serialNumber,deviceRole"))
            rp_dict = json.loads(self.exec_cmd(
                "inventory-action.pl -q -use_krb_auth -resource hostconfig -action read -host.name " + hostname + " -fields key,value -key rackUPos"))
            cc_dict = json.loads(self.exec_cmd("inventory-action.pl -q -use_krb_auth -resource host -action read -host.name " +
                                               hostname + " -fields cluster.clusterConfigs.value,cluster.clusterConfigs.type"))
            sm_dict = json.loads(self.exec_cmd(
                "inventory-action.pl -q -use_krb_auth -resource host -action read -host.name " + hostname + " -fields manufacturer"))
            logger.info("Got info for %s from iDB" % hostname)
            cnc_api_url = str(ci_dict["data"][0]["value"])
            serial_number = str(sn_dict["data"][0]["serialNumber"])
            device_role = str(sn_dict["data"][0]["deviceRole"])
            rack_position = str(rp_dict["data"][0]["value"])
            manufacturer = str(sm_dict["data"][0]["manufacturer"])
            network_domain = "ops.sfdc.net"
            cluster_configs_list = list(
                cc_dict["data"][0]["cluster"]["clusterConfigs"])
            for i in cluster_configs_list:
                if "network-domain" in i.values():
                    network_domain = i["value"]
                    if network_domain == None or network_domain == "":
                        network_domain = "ops.sfdc.net"
            output.setdefault(str(hostname), {"cnc_api_url": cnc_api_url, "serial_number": serial_number, "device_role": device_role,
                                              "rack_position": rack_position, "network_domain": network_domain, "manufacturer": manufacturer})
            status = "SUCCESS"
        except ValueError:
            logger.debug(
                "Error: unable to find racktastic apiUrl/serialNumber of %s in iDB" % hostname)
            output.setdefault(str(hostname), {"cnc_api_url": None, "serial_number": None, "device_role": None,
                                              "rack_position": None, "network_domain": None, "manufacturer": None})
            status = "ERROR"
        except:
            logger.debug(
                "Error: unable to find racktastic apiUrl/serialNumber of %s in iDB" % hostname)
            output.setdefault(str(hostname), {"cnc_api_url": None, "serial_number": None, "device_role": None,
                                              "rack_position": None, "network_domain": None, "manufacturer": None})
            status = "ERROR"
        return output, status

    def route_check(self, hostname, casenum):
        """
        For a given host, this method checks if the host is reachable via ssh from within cnc
        """
        output = {}
        status = None

        certsExist = self._validate_certs(self.mtls_props)
        if not certsExist:
            status = "ERROR"
            output.setdefault("error", "PKI certs for current user %s not found or inaccessible." % self.current_user)
            return output, status
        cert = (self.mtls_props["cert"], self.mtls_props["key"])
        capath = self.mtls_props["capath"]

        isHostProp, host_props = self._read_host_props(casenum, hostname)
        if not isHostProp:
            output.setdefault("error", "couldn't find any details regarding %s in %s_hostinfo." % (hostname, casenum))
            status = "ERROR"
        else:
            cnc_api_url = host_props["cnc_api_url"]
            serial_number = host_props["serial_number"]

            cnc_host = cnc_api_url.split("//")[1].split(":")[0]
            route_check_url = cnc_api_url + "diagnostic/bmc/" + serial_number
            try:
                response = requests.get(route_check_url, cert=cert, verify=capath)
                if not (response.status_code >= 200 and response.status_code <= 300):
                    raise Exception
                result = response.json()
                accessible = result["accessible"]
                authenticable = result["authenticatable"]

                if accessible == True and authenticable == True:
                    output.setdefault(
                        "success", "%s - Route check passed and IB console is accessible" % hostname)
                    status = "SUCCESS"
                else:
                    status = "ERROR"
                    error_msg = "BMC Check for %s:\n"
                    if not accessible:
                        error_msg += "accessible - False\n"
                    if not authenticable:
                        error_msg += "authenticable - False\n"
                    output.setdefault(
                        "error", error_msg % hostname)
            except:
                output.setdefault(
                    "error", "%s - an error occured while processing the request on %s" % (hostname, cnc_host))
                status = "ERROR"

        return output, status

    def trigger_image(self, hostname, casenum, role="", preserve=False, disk_config="", no_op=False):
        """
        For a given host this method triggers image event on cnc api url and validates whether that event successfully completed or not
        """

        output = {}
        status = None

        certsExist = self._validate_certs(self.mtls_props)
        if not certsExist:
            status = "ERROR"
            output.setdefault("error", "PKI certs for current user %s not found or inaccessible." % self.current_user)
            return output, status
        cert = (self.mtls_props["cert"], self.mtls_props["key"])
        capath = self.mtls_props["capath"]
        mtls_certs = "--capath %s --cert %s --key %s" % (
            self.mtls_props["capath"], self.mtls_props["cert"], self.mtls_props["key"])

        isHostProp, host_props = self._read_host_props(casenum, hostname)
        if not isHostProp:
            output.setdefault("error", "couldn't find any details regarding %s in %s_hostinfo." % (hostname, casenum))
            status = "ERROR"
        else:
            cnc_api_url = host_props["cnc_api_url"]
            serial_number = host_props["serial_number"]
            device_role = host_props["device_role"]

            right_data_options = self._validate_role_props(
                hostname, role, disk_config, preserve, host_props, command="image")
            if not right_data_options:
                output.setdefault("error", "%s - Failed to meet Data Preservation/Disk Config criteria." % hostname)
                status = "ERROR"
                return output, status

            rack_status = self.check_rack_status(cnc_api_url)
            logger.info("%s - %s" % (cnc_api_url, rack_status))
            if not rack_status in ["ready"]:
                output.setdefault(
                    "error", "The rack status does not match it's expected state: 'ready' <> '%s'. Exiting." % rack_status)
                return output, "ERROR"
            else:
                payload = dict()
                payload.update({"type": "image", "serial_number": serial_number, "message": {}})

                if role != None:
                    payload["message"].update({"name": "vanilla", "preserve": str(
                        preserve).lower(), "host_role": role, "disk_config": disk_config})
                else:
                    payload["message"].update({"name": "vanilla", "preserve": str(
                        preserve).lower(), "disk_config": disk_config})
                image_cmd = "curl %s -s --request POST %sevent -d '%s'" % (mtls_certs, cnc_api_url, json.dumps(payload))
                if not no_op:
                    logger.info("Image command - %s", image_cmd)
                    try:
                        url = "%sevent" % cnc_api_url
                        response = requests.post(url, data=json.dumps(payload), cert=cert, verify=capath)
                        if not (response.status_code >= 200 and response.status_code <= 300):
                            raise Exception
                        else:
                            image_cmd_response = response.json()
                            cnc_host = cnc_api_url.split("//")[1].split(".")[0]
                            event_type = image_cmd_response["type"]
                            event_id = image_cmd_response["id"]
                            event_status = image_cmd_response["status"]
                            logger.info("%s - [%s] %s -- %s" % (hostname, event_id, event_type, event_status))
                            event_api_url = "%sevent/%s" % (cnc_api_url, event_id)
                            e_result, e_status = self.check_event_status(event_api_url)
                            logger.info("%s - %s" % (hostname, e_status))
                            if e_result == True:
                                if e_status == "completed":
                                    status = "SUCCESS"
                                    output.setdefault("success", "%s event %s processing on %s" %
                                                      (event_type, e_status, hostname))
                                elif e_status == "failed":
                                    status = "ERROR"
                                    output.setdefault("error", "%s to process %s event on %s due to some error. \nCNC Host - %s\nSerial Number - %s" % (
                                        e_status, event_type, hostname, cnc_host, serial_number))
                            else:
                                status = "ERROR"
                                output.setdefault("message", "%s event not processed within time on %s. \nCheck manually at %s" % (
                                    event_type, hostname, event_api_url))
                    except Exception:
                        output.setdefault("error", "an error occured while processing request - %s" % url)
                        status = "ERROR"
                else:
                    status = "SUCCESS"
                    output.setdefault("dry_run", "%s - %s" % (hostname, image_cmd))
        return output, status

    def fail_host(self, hostname, casenum, no_op=False):
        """
        For any given host, this method triggers fail_host event on cnc api url that would update the host racktastic status to failed
        """
        output = {}
        status = None

        certsExist = self._validate_certs(self.mtls_props)
        if not certsExist:
            status = "ERROR"
            output.setdefault("error", "PKI certs for current user %s not found or inaccessible." % self.current_user)
            return output, status
        cert = (self.mtls_props["cert"], self.mtls_props["key"])
        capath = self.mtls_props["capath"]
        mtls_certs = "--capath %s --cert %s --key %s" % (
            self.mtls_props["capath"], self.mtls_props["cert"], self.mtls_props["key"])

        isHostProp, host_props = self._read_host_props(casenum, hostname)
        if not isHostProp:
            output.setdefault("error", "couldn't find any details regarding %s in %s_hostinfo." % (hostname, casenum))
            status = "ERROR"
        else:
            cnc_api_url = host_props["cnc_api_url"]
            serial_number = host_props["serial_number"]

            rack_status = self.check_rack_status(cnc_api_url)
            logger.info("%s - %s" % (cnc_api_url, rack_status))
            if not rack_status in ["ready"]:
                output.setdefault(
                    "error", "The rack status does not match it's expected state: 'ready' <> '%s'. Exiting." % rack_status)
                return output, "ERROR"
            else:
                payload = dict()
                payload.update({"type": "fail_host", "serial_number": serial_number})

                fail_host_cmd = "curl %s -s --request POST %sevent -d '%s'" % (
                    mtls_certs, cnc_api_url, json.dumps(payload))
                if not no_op:
                    logger.info("fail_host - %s", fail_host_cmd)
                    try:
                        url = "%sevent" % cnc_api_url
                        response = requests.post(url, data=json.dumps(payload), cert=cert, verify=capath)
                        if not (response.status_code >= 200 and response.status_code <= 300):
                            raise Exception
                        else:
                            fail_host_cmd_response = response.json()
                            cnc_host = cnc_api_url.split("//")[1].split(".")[0]
                            event_type = fail_host_cmd_response["type"]
                            event_id = fail_host_cmd_response["id"]
                            event_status = fail_host_cmd_response["status"]
                            logger.info("%s - [%s] %s -- %s" %
                                        (hostname, event_id, event_type, event_status))
                            event_api_url = "%sevent/%s" % (cnc_api_url, event_id)
                            e_result, e_status = self.check_event_status(event_api_url)
                            logger.info("%s - %s" % (hostname, e_status))
                            if e_result == True:
                                if e_status == "completed":
                                    status = "SUCCESS"
                                    output.setdefault("success", "%s event %s processing on %s" %
                                                      (event_type, e_status, hostname))
                                elif e_status == "failed":
                                    status = "ERROR"
                                    output.setdefault("error", "%s to process %s event on %s due to some error. \n CNC Host - %s\nSerial Number - %s" % (
                                        e_status, event_type, hostname, cnc_host, serial_number))
                            else:
                                status = "ERROR"
                                output.setdefault("message", "%s event not processed within time on %s. \nCheck manually at %s" % (
                                    event_type, hostname, event_api_url))
                    except Exception:
                        output.setdefault("error", "an error occured while processing request - %s" % url)
                        status = "ERROR"
                else:
                    status = "SUCCESS"
                    output.setdefault("dry_run", "%s - %s" % (hostname, fail_host_cmd))
        return output, status

    def rebuild_failed_host(self, hostname, casenum, preserve=False, disk_config="", no_op=False):
        """
        For a given host that has racktastic status as failed, this method triggers rebuild_failed_host event on cnc api url and validates whether that successfully completed or not
        """
        output = {}
        status = None

        certsExist = self._validate_certs(self.mtls_props)
        if not certsExist:
            status = "ERROR"
            output.setdefault("error", "PKI certs for current user %s not found or inaccessible." % self.current_user)
            return output, status
        cert = (self.mtls_props["cert"], self.mtls_props["key"])
        capath = self.mtls_props["capath"]
        mtls_certs = "--capath %s --cert %s --key %s" % (
            self.mtls_props["capath"], self.mtls_props["cert"], self.mtls_props["key"])

        isHostProp, host_props = self._read_host_props(casenum, hostname)
        if not isHostProp:
            output.setdefault("error", "couldn't find any details regarding %s in %s_hostinfo." % (hostname, casenum))
            status = "ERROR"
        else:
            cnc_api_url = host_props["cnc_api_url"]
            serial_number = host_props["serial_number"]

            right_data_options = self._validate_role_props(
                hostname, None, disk_config, preserve, host_props, command="rebuild")
            if not right_data_options:
                output.setdefault("error", "%s - Failed to meet Data Preservation/Disk Config criteria." % hostname)
                status = "ERROR"
                return output, status

            rack_status = self.check_rack_status(cnc_api_url)
            if not rack_status in ["ready"]:
                output.setdefault(
                    "error", "The rack status does not match it's expected state: 'ready' <> '%s'. Exiting." % rack_status)
                return output, "ERROR"
            else:
                payload = dict()
                payload.update({"type": "rebuild_failed_host", "serial_number": serial_number, "message": {}})
                payload["message"].update({"name": "vanilla", "preserve": str(
                    preserve).lower(), "disk_config": disk_config})

                rebuild_cmd = "curl %s -s --request POST %sevent -d '%s'" % (
                    mtls_certs, cnc_api_url, json.dumps(payload))
                if not no_op:
                    logger.info("rebuild command - %s ", rebuild_cmd)
                    try:
                        url = "%sevent" % cnc_api_url
                        response = requests.post(url, data=json.dumps(payload), cert=cert, verify=capath)
                        if not (response.status_code >= 200 and response.status_code <= 300):
                            raise Exception
                        else:
                            rebuild_cmd_response = response.json()
                            cnc_host = cnc_api_url.split("//")[1].split(".")[0]
                            event_type = rebuild_cmd_response["type"]
                            event_id = rebuild_cmd_response["id"]
                            event_status = rebuild_cmd_response["status"]
                            logger.info("%s - [%s] %s -- %s" %
                                        (hostname, event_id, event_type, event_status))
                            event_api_url = "%sevent/%s" % (cnc_api_url, event_id)
                            e_result, e_status = self.check_event_status(event_api_url)
                            logger.info("%s - %s" % (hostname, e_status))
                            if e_result == True:
                                if e_status == "completed":
                                    status = "SUCCESS"
                                    output.setdefault("success", "%s event %s processing on %s" %
                                                      (event_type, e_status, hostname))
                                elif e_status == "failed":
                                    status = "ERROR"
                                    output.setdefault("error", "%s to process %s event on %s due to some error. \nCNC Host - %s\nSerial Number - %s" % (
                                        e_status, event_type, hostname, cnc_host, serial_number))
                            else:
                                status = "ERROR"
                                output.setdefault("message", "%s event not processed within time on %s. \nCheck manually at %s" % (
                                    event_type, hostname, event_api_url))
                    except Exception:
                        output.setdefault("error", "an error occured while processing request - %s" % url)
                        status = "ERROR"
                else:
                    status = "SUCCESS"
                    output.setdefault("dry_run", "%s - %s" % (hostname, rebuild_cmd))
        return output, status

    def trigger_deploy(self, hostname, casenum, role="", cluster="", superpod="", preserve=False, no_op=False):
        """
        For a given host, this method triggers deploy event on cnc api url and validates whether it is completed or not.
        """
        output = {}
        status = None

        certsExist = self._validate_certs(self.mtls_props)
        if not certsExist:
            status = "ERROR"
            output.setdefault("error", "PKI certs for current user %s not found or inaccessible." % self.current_user)
            return output, status
        cert = (self.mtls_props["cert"], self.mtls_props["key"])
        capath = self.mtls_props["capath"]
        mtls_certs = "--capath %s --cert %s --key %s" % (
            self.mtls_props["capath"], self.mtls_props["cert"], self.mtls_props["key"])

        isHostProp, host_props = self._read_host_props(casenum, hostname)
        if not isHostProp:
            output.setdefault("error", "couldn't find any details regarding %s in %s_hostinfo." % (hostname, casenum))
            status = "ERROR"
        else:
            cnc_api_url = host_props["cnc_api_url"]
            serial_number = host_props["serial_number"]
            network_domain = host_props["network_domain"]

            right_data_options = self._validate_role_props(hostname, role, None, preserve, host_props, command="deploy")
            if not right_data_options:
                output.setdefault("error", "%s - Failed to meet Data Preservation criteria." % hostname)
                status = "ERROR"
                return output, status

            host_fqdn = "%s.%s" % (hostname, network_domain)
            rack_status = self.check_rack_status(cnc_api_url)
            if not rack_status in ["ready"]:
                output.setdefault(
                    "error", "The rack status does not match it's expected state: 'ready' <> '%s'. Exiting." % rack_status)
                return output, "ERROR"
            else:
                payload = dict()
                payload.update({"type": "deploy", "serial_number": serial_number, "message": {}})
                payload["message"].update({"inventory_idb_cluster_name": cluster, "inventory_idb_superpod_name": superpod,
                                           "default_hostname": host_fqdn, "host_role": role, "preserve": str(preserve).lower()})

                deploy_cmd = "curl %s -s --request POST %sevent -d '%s'" % (
                    mtls_certs, cnc_api_url, json.dumps(payload))
                if not no_op:
                    logger.info("Deploy command - %s", deploy_cmd)

                    try:
                        url = "%sevent" % cnc_api_url
                        response = requests.post(url, data=json.dumps(payload), cert=cert, verify=capath)
                        if not (response.status_code >= 200 and response.status_code <= 300):
                            raise Exception
                        else:
                            deploy_cmd_response = response.json()
                            cnc_host = cnc_api_url.split("//")[1].split(".")[0]
                            event_type = deploy_cmd_response["type"]
                            event_id = deploy_cmd_response["id"]
                            event_status = deploy_cmd_response["status"]
                            logger.info("%s - [%s] %s -- %s" %
                                        (hostname, event_id, event_type, event_status))
                            event_api_url = "%sevent/%s" % (cnc_api_url, event_id)
                            e_result, e_status = self.check_event_status(event_api_url)
                            logger.info("%s - %s" % (hostname, e_status))
                            if e_result == True:
                                if e_status == "completed":
                                    status = "SUCCESS"
                                    output.setdefault("success", "%s event %s processing on %s" % (
                                        event_type, e_status, hostname))
                                elif e_status == "failed":
                                    status = "ERROR"
                                    output.setdefault("error", "%s to process %s event on %s due to some error. \nCNC Host - %s\nSerial Number - %s" % (
                                        e_status, event_type, hostname, cnc_host, serial_number))
                            else:
                                status = "ERROR"
                                output.setdefault("message", "%s event not processed within time on %s. \nCheck manually at %s" % (
                                    event_type, hostname, event_api_url))
                    except Exception:
                        output.setdefault("error", "an error occured while processing request - %s" % url)
                        status = "ERROR"
                else:
                    status = "SUCCESS"
                    output.setdefault("dry_run", "%s - %s" % (hostname, deploy_cmd))
        return output, status

    def erase_hostname(self, hostname, casenum):
        """
        For a given host, this method erases the hostname in iDB in order to deploy
        """
        output = {}
        status = None
        isHostProp, host_props = self._read_host_props(casenum, hostname)
        if not isHostProp:
            output.setdefault("error", "couldn't find any details regarding %s in %s_hostinfo." % (hostname, casenum))
            status = "ERROR"
        else:
            serial_number = host_props["serial_number"]

            hname = ""
            verify_cmd = "inventory-action.pl -q -use_krb_auth -resource host -action read -serialNumber %s -fields name" % serial_number
            try:
                verify_cmd_response = json.loads(self.exec_cmd(verify_cmd))
                hname = verify_cmd_response["data"][0]["name"]
            except ValueError:
                # handles the null values if iDB returns empty
                hname == ""
            if hname == None:
                output.setdefault(
                    "success", "hostname is already null in iDB for host %s" % hostname)
                status = "SUCCESS"
            else:
                try:
                    erase_cmd = "inventory-action.pl -q -use_krb_auth -resource host -action update -serialNumber %s -updateFields \"name=null\"" % serial_number
                    self.exec_cmd(erase_cmd)
                    logger.debug("%s - payload sent to erase" % hostname)
                    verify_cmd2_response = json.loads(self.exec_cmd(verify_cmd))
                    if verify_cmd2_response["data"][0]["name"] == None:
                        output.setdefault(
                            "success", "%s hostname erased successfully" % hostname)
                        status = "SUCCESS"
                    else:
                        output.setdefault(
                            "error", "unable to erase hostname for %s due to some error" % hostname)
                        status = "ERROR"
                except:
                    output.setdefault(
                        "error", "%s - an error occured while processing the request" % hostname)
                    status = "ERROR"
        return output, status

    def update_idb_status(self, hostname, casenum, idb_status="ACTIVE"):
        """
        For a given host, this method updates the host operatiioinal status in iDB with provided status
        """
        output = {}
        status = None
        isHostProp, host_props = self._read_host_props(casenum, hostname)
        if not isHostProp:
            output.setdefault("error", "couldn't find any details regarding %s in %s_hostinfo." % (hostname, casenum))
            status = "ERROR"
        else:
            serial_number = host_props["serial_number"]

            max_retries = 30 if idb_status == "ACTIVE" else 3
            interval = 60
            count = 0
            old_status = ""
            old_status_cmd = "inventory-action.pl -q -use_krb_auth -resource host -action read -serialNumber %s -fields operationalStatus" % serial_number

            if idb_status == "ACTIVE":
                # puts the host back to ACTIVE once the puppet runs finshes after migration
                prev_status = ["PROVISIONING", "IN_MAINTENANCE"]

                logger.info("Checking for %s iDB status to update to %s" % (hostname, "/".join(prev_status)))
                while not old_status in prev_status:
                    if count == max_retries:
                        output.setdefault(
                            "error", "iDB status was not changed to %s by puppet within time. Please retry/check manually." % "/".join(prev_status))
                        status = "ERROR"
                        return output, status

                    try:
                        old_status_cmd_response = json.loads(self.exec_cmd(old_status_cmd))
                        old_status = old_status_cmd_response["data"][0]["operationalStatus"]
                    except ValueError:
                        # handles null value if iDB returns empty
                        old_status = ""

                    if old_status in prev_status:
                        desired_status_position = prev_status.index(old_status)
                        desired_status = prev_status[desired_status_position]
                        logger.info("%s iDB status matched with desired status '%s' == '%s'" %
                                    (hostname, desired_status, old_status))
                        break

                    if old_status == idb_status:
                        output.setdefault(
                            "success", "%s iDB status is already '%s'. Cross-verify the host manually." % (hostname, idb_status))
                        status = "SUCCESS"
                        return output, status

                    logger.info("%s iDB status does not match desired status '%s' <> '%s'" %
                                (hostname, "/".join(prev_status), old_status))
                    logger.info("Retrying in %s seconds" % (interval))
                    time.sleep(interval)
                    count += 1

            try:
                update_cmd = "inventory-action.pl -q -use_krb_auth -resource host -action update -serialNumber %s -updateFields \"operationalStatus=%s\"" % (
                    serial_number, idb_status)
                self.exec_cmd(update_cmd)
                logger.debug("%s - payload sent to update iDB status to %s" % (hostname, idb_status))
                new_status = json.loads(self.exec_cmd(old_status_cmd))["data"][0]["operationalStatus"]
                if new_status == idb_status:
                    output.setdefault("success", "%s - iDB status successfully updated to %s" % (hostname, new_status))
                    status = "SUCCESS"
                else:
                    output.setdefault("error", "%s - failed to change iDB Status to '%s' <> '%s'" %
                                      (hostname, idb_status, new_status))
                    status = "ERROR"
            except:
                output.setdefault("error", "%s - an error occurred while processing the request" % hostname)
                status = "ERROR"
        return output, status

    def check_idb_status(self, hostname, casenum, expected_idb_status="ACTIVE"):
        """
        For a given, this method checks it's iDB status matches expected status
        """
        output = {}
        status = None
        isHostProp, host_props = self._read_host_props(casenum, hostname)
        if not isHostProp:
            output.setdefault("error", "couldn't find any details regarding %s in %s_hostinfo." % (hostname, casenum))
            status = "ERROR"
        else:
            serial_number = host_props["serial_number"]

            max_retries = 30 if expected_idb_status == "PROVISIONING" else 3
            interval = 60 if expected_idb_status == "PROVISIONING" else 5
            count = 0
            idb_status = ""
            idb_status_cmd = "inventory-action.pl -q -use_krb_auth -resource host -action read -serialNumber %s -fields operationalStatus" % serial_number

            while idb_status != expected_idb_status:
                if count == max_retries:
                    output.setdefault(
                        "error", "%s iDB status does not match desired status '%s' <> '%s'" % (hostname, expected_idb_status, idb_status))
                    status = "ERROR"
                    return output, status

                try:
                    idb_status_cmd_response = json.loads(self.exec_cmd(idb_status_cmd))
                    idb_status = idb_status_cmd_response["data"][0]["operationalStatus"]
                except ValueError:
                    # handles null value if iDB returns empty
                    idb_status = ""

                if idb_status == expected_idb_status:
                    output.setdefault("success", "%s iDB status matched with desired status '%s' == '%s'" %
                                      (hostname, expected_idb_status, idb_status))
                    status = "SUCCESS"
                    return output, status

                logger.info("%s iDB status does not match desired status '%s' <> '%s'" %
                            (hostname, expected_idb_status, idb_status))
                logger.info("Retrying in %s seconds" % (interval))
                time.sleep(interval)
                count += 1
        return output, status

    def check_status(self, hostname, casenum, delay, prev_cmd):
        """
        For a given host, this method checks for the status changes in racktastic
        """
        output = {}
        status = None

        certsExist = self._validate_certs(self.mtls_props)
        if not certsExist:
            status = "ERROR"
            output.setdefault("error", "PKI certs for current user %s not found or inaccessible." % self.current_user)
            return output, status
        cert = (self.mtls_props["cert"], self.mtls_props["key"])
        capath = self.mtls_props["capath"]

        isHostProp, host_props = self._read_host_props(casenum, hostname)
        if not isHostProp:
            output.setdefault("error", "couldn't find any details regarding %s in %s_hostinfo." % (hostname, casenum))
            status = "ERROR"
        else:
            cnc_api_url = host_props["cnc_api_url"]
            serial_number = host_props["serial_number"]

            logger.info("%s - %s, %s" % (hostname, serial_number, cnc_api_url))
            rack_status = self.check_rack_status(cnc_api_url)
            if not rack_status in ["ready"]:
                output.setdefault(
                    "error", "The rack status does not match it's expected state: 'ready' <> '%s'. Exiting." % rack_status)
                return output, "Rack - %s" % rack_status
            else:
                poll_interval = 60
                retry_count = 20
                count = 0
                result = False
                status = None
                logger.info("Pausing %s seconds for the status to change" % delay)
                time.sleep(delay)
                while result != True:
                    url = "%shost/%s" % (cnc_api_url, serial_number)
                    status_cmd = "curl -s --request GET %s" % url
                    try:
                        response = requests.get(url, cert=cert, verify=capath)
                        if not (response.status_code >= 200 and response.status_code <= 300):
                            raise Exception
                        else:
                            status_cmd_response = response.json()
                            status = status_cmd_response["state"]
                            logger.info("%s - %s" % (hostname, status))
                            if prev_cmd in ["image", "rebuild"] and status == "awaiting_deployment":
                                result = True
                                output.setdefault(
                                    "success", "%s processed successfully. latest status after %s command - %s" % (hostname, prev_cmd, status))
                                break
                            elif prev_cmd == "deploy" and status == "deployed":
                                result = True
                                output.setdefault(
                                    "success", "%s processed successfully. latest status after %s command - %s" % (hostname, prev_cmd, status))
                                break
                            elif prev_cmd == "fail" and status == "failed":
                                result = True
                                output.setdefault(
                                    "success", "%s processed successfully. latest status after %s command - %s" % (hostname, prev_cmd, status))
                                break
                            logger.info("Retrying in %s seconds " % (poll_interval))
                            time.sleep(poll_interval)
                            count += 1
                            if prev_cmd in ["image", "rebuild", "deploy"] and status == "failed":
                                result = True
                                output.setdefault("error", "%s failed to process. latest status after %s command - %s" %
                                                  (hostname, prev_cmd, status))
                                break
                            if prev_cmd in ["image", "rebuild"] and count > 10:
                                logger.info(
                                    "%s might be stuck at awaiting_checkin. Please check in console" % hostname)
                            if count == retry_count:
                                logger.info(
                                    "%s status didn't change in expected time. Please retry" % hostname)
                                output.setdefault(
                                    "message", "unable to process %s in time." % hostname)
                                result = True
                    except Exception:
                        output.setdefault("error", "an error occured while processing request - %s" % url)
                        status = "ERROR"
        return output, status

    def check_event_status(self, event_api_url):
        delay = 60
        poll_interval = 30
        retry_count = 60
        count = 0
        result = False
        status = None

        certsExist = self._validate_certs(self.mtls_props)
        if not certsExist:
            result = False
            status = "Missing PKI Certs"
            logger.error("PKI certs for current user %s not found or inaccessible." % self.current_user)
            return result, status
        cert = (self.mtls_props["cert"], self.mtls_props["key"])
        capath = self.mtls_props["capath"]

        logger.info("Pausing %s seconds for the event status to change" % delay)
        time.sleep(delay)
        while result != True:
            response = requests.get(event_api_url, timeout=30, cert=cert, verify=capath)
            if (response.status_code >= 200 and response.status_code <= 300):
                res = response.json()
                status = res["status"]
                if status in ["completed", "failed"]:
                    result = True
                    break
                logger.info("%s - %s\nRetrying in %s seconds " % (event_api_url, status, poll_interval))
                time.sleep(poll_interval)
                count += 1
                if count == retry_count:
                    logger.info("Event status does not match desired status - 'completed' <> '%s'" % status)
                    result = False
                    break
            else:
                logger.error("an error occured while checking event status")
                result = False
                status = "error"
                break
        return result, status

    def check_rack_status(self, cnc_api_url):

        certsExist = self._validate_certs(self.mtls_props)
        if not certsExist:
            logger.error("PKI certs for current user %s not found or inaccessible." % self.current_user)
            return "PKI Certs Missing"
        cert = (self.mtls_props["cert"], self.mtls_props["key"])
        capath = self.mtls_props["capath"]

        cnc_host = cnc_api_url.split("//")[1].split(".")[0]
        rack_status_url = cnc_api_url + "status"
        count = 0
        max_retries = 3
        logger.info("Checking rack status on %s. Will be retrying a maximum of %s times if timed out." %
                    (cnc_host, max_retries))
        delay = 30
        try:
            while count != max_retries:
                response = requests.get(rack_status_url, timeout=30, cert=cert, verify=capath)
                if not (response.status_code >= 200 and response.status_code <= 300):
                    if count == max_retries:
                        raise Exception
                    count += 1
                    time.sleep(delay)
                else:
                    result = response.json()
                    rack_status = result["rack"]["state"]
                    logger.info("Rack Status of %s - %s" % (cnc_host, rack_status))
                    return rack_status
        except:
            logger.error(
                "The rack status of %s could not be fetched in time. Exiting." % cnc_host)
            return "timed out"

    def validate_disk_config(self, hostname, casenum, disk_config_to_validate):
        """
        This method to check the disk config of given hostname and match with given state
        :return:
        """
        output = {}
        status = None

        certsExist = self._validate_certs(self.mtls_props)
        if not certsExist:
            status = "ERROR"
            output.setdefault("error", "PKI certs for current user %s not found or inaccessible." % self.current_user)
            return output, status
        cert = (self.mtls_props["cert"], self.mtls_props["key"])
        capath = self.mtls_props["capath"]

        isHostProp, host_props = self._read_host_props(casenum, hostname)
        if not isHostProp:
            output.setdefault("error", "couldn't find any details regarding %s in %s_hostinfo." % (hostname, casenum))
            status = "ERROR"
        else:
            cnc_api_url = host_props["cnc_api_url"]
            serial_number = host_props["serial_number"]

            cnc_host = cnc_api_url.split("//")[1].split(":")[0]
            disk_config_url = cnc_api_url + "fact/device/" + serial_number + "/disk_config"
            try:
                response = requests.get(disk_config_url, cert=cert, verify=capath)
                if not (response.status_code >= 200 and response.status_code <= 300):
                    raise Exception
                result = response.json()
                d_config = result["disk_config"]
                if d_config and d_config == disk_config_to_validate:
                    output.setdefault("success", "Disk config for host %s matched %s == %s" %
                                      (hostname, d_config, disk_config_to_validate))
                    status = "SUCCESS"
                else:
                    status = "ERROR"
                    error_msg = "Disk Layout doesn't match %s <> %s"
                    output.setdefault(
                        "error", error_msg % (d_config, disk_config_to_validate))
            except:
                output.setdefault(
                    "error", "%s - an error occured while processing the request on %s" % (hostname, cnc_host))
                status = "ERROR"

        return output, status

    def validate_nic(self, hostname, casenum, mac_addr_info):
        """
        This method validates the IB/Host Mac address in CNC against the data in host
        """
        output = {}
        status = None

        certsExist = self._validate_certs(self.mtls_props)
        if not certsExist:
            status = "ERROR"
            output.setdefault("error", "PKI certs for current user %s not found or inaccessible." % self.current_user)
            return output, status
        cert = (self.mtls_props["cert"], self.mtls_props["key"])
        capath = self.mtls_props["capath"]

        isHostProp, host_props = self._read_host_props(casenum, hostname)
        if not isHostProp:
            output.setdefault("error", "couldn't find any details regarding %s in %s_hostinfo." % (hostname, casenum))
            status = "ERROR"
        else:
            cnc_api_url = host_props["cnc_api_url"]
            serial_number = host_props["serial_number"]

            cnc_host = cnc_api_url.split("//")[1].split(":")[0]
            host_fact_url = cnc_api_url + "fact/device/" + serial_number
            macaddress_ib = ""
            macaddress_host = ""
            try:
                response = requests.get(host_fact_url, cert=cert, verify=capath)
                if not (response.status_code >= 200 and response.status_code <= 300):
                    raise Exception
                result = response.json()
                macaddress_ib = str(result["macaddress_ib"]).upper()
                macaddress_host = str(result["macaddress"]).upper()

                for item in mac_addr_info:
                    if str(item) == hostname:
                        mac_ib = mac_addr_info[str(item)]["IB_MAC_ADDRESS"].upper()
                        mac_host = mac_addr_info[str(item)]["HOST_MAC_ADDRESS"].upper()
                        break
                if macaddress_host == mac_host and macaddress_ib == mac_ib:
                    logger.info("%s - IB MAC matched. RT! '%s' == HOST '%s'" % (hostname, macaddress_ib, mac_ib))
                    logger.info("%s - HOST MAC matched. RT! '%s' == HOST '%s'" % (hostname, macaddress_host, mac_host))
                    output.setdefault("success", "NIC Configs matched")
                    status = "SUCCESS"
                else:
                    if not (macaddress_ib == mac_ib):
                        logger.error("%s - IB MAC didn't match. RT! '%s' <> HOST '%s'" %
                                     (hostname, macaddress_ib, mac_ib))
                    else:
                        logger.info("%s - IB MAC matched. RT! '%s' == HOST '%s'" % (hostname, macaddress_ib, mac_ib))

                    if not (macaddress_host == mac_host):
                        logger.error("%s - HOST MAC didn't match. RT! '%s' <> HOST '%s'" %
                                     (hostname, macaddress_host, mac_host))
                    else:
                        logger.info("%s - HOST MAC matched. RT! '%s' == HOST '%s'" %
                                    (hostname, macaddress_host, mac_host))
                    output.setdefault("error", "MAC address(es) didn't match")
                    status = "ERROR"
            except Exception:
                output.setdefault("error", "an error occured while fetching MAC Info from %s" % cnc_host)
                status = "ERROR"
        return output, status


def main():
    """
    This is main method which will accept the command line argument and pass to the class methods.
    """

    parser = ArgumentParser(prog='migration_manager.py',
                            usage="\n %(prog)s \n\t-h --help prints this help \n\t"
                                  "-v verbose output \n\t"
                                  "-c casenum -a cncinfo \n\t-"
                                  "-c casenum -a routecheck \n\t"
                                  "-c casenum -a image [--role <ROLE>] [--preserve] [--disk_config <default is stage1v0>] [--dry-run] \n\t"
                                  "-c casenum -a deploy --role <ROLE> --cluster <CLUSTER> --superpod <SUPERPOD> [--preserve] [--dry-run] \n\t"
                                  "-c casenum -a fail [--dry-run] \n\t"
                                  "-c casenum -a rebuild [--preserve] [--disk_config <default is stage1v0>] [--dry-run] \n\t"
                                  "-c casenum -a status [--delay <MINS> default is 10] --previous <PREVIOUS_ACTION>\n\t"
                                  "-c casenum -a erasehostname \n\t"
                                  "-c casenum -a updateopsstatus --status <STATUS> \n\t"
                                  "-c casenum -a idb_check --status <STATUS> \n\t"
                                  "-c casenum -a validate_nic \n\t"
                                  "-c casenum -a check_disk_config --disk_config <disk_config> \n\t")

    parser.add_argument("-c", dest="case", help="case number", required=True)
    parser.add_argument("-a", dest="action", help="specify intended action", required=True,
                        choices=["cncinfo", "routecheck", "image", "fail", "deploy", "rebuild", "status", "erasehostname", "updateopsstatus", "idb_check", "check_disk_config", "validate_nic"])
    parser.add_argument("--role", dest="host_role", help="specify host role")
    parser.add_argument("--cluster", dest="cluster_name",
                        help="specify cluster name")
    parser.add_argument("--superpod", dest="superpod_name",
                        help="specify super pod name")
    parser.add_argument("--disk_config", dest="disk_config",
                        help="specify disk config e.g stage1v0", choices=["standard", "stage1v0", "fastcache2", "stage1hdfs", "hdfs"], default="stage1v0")
    parser.add_argument("--preserve", dest="preserve_data", action="store_true",
                        help="include this to preserve data", default=False)
    parser.add_argument("--delay", dest="delay_in_mins",
                        type=int, default=10, help="specify delay in minutes")
    parser.add_argument("--previous", dest="prev_action", help="specify previous racktastic command perfomred",
                        choices=["image", "deploy", "rebuild", "fail"])
    parser.add_argument("--status", dest="idb_status", help="specify idb status", choices=[
                        'ACTIVE', 'DECOM', 'PROVISIONING', 'HW_PROVISIONING', 'IN_MAINTENANCE', 'REIMAGE'], default="ACTIVE")
    parser.add_argument("--dry-run", dest="no_op",
                        help="prints the payload of your request. works with RT! image, deploy, rebuild and fail commands.", action="store_true", default=False)
    parser.add_argument("-v", dest="verbose", action="store_true",
                        help="verbose output", default=False)

    args = parser.parse_args()

    user_home = path.expanduser("~")

    # setting up default logging level for the rest of the program
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    misc = Util()
    # validating for existing kerberos tickets
    if not misc.has_valid_kerberos_ticket():
        logger.error("Please kinit to continue. Exiting.")
        sys.exit(1)

    casenum = str(args.case)
    # action = str(args.action)

    host_list = misc.read_hostlist_from_file(casenum, type="include")
    thread_count = len(host_list)  # number of parallel threads

    if args.action == "cncinfo":
        if not misc.check_file_exists(casenum, type="include"):
            logger.error("%s/%s_include file not found or inaccessible" %
                         (user_home, casenum))
            sys.exit(1)
        hosts_processed = {}
        queue = Queue.Queue()

        for i in range(thread_count):
            logger.debug("thread - %d", i)
            t = ThreadCncInfo(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            queue.put(h)
        queue.join()

        include_list = []
        exclude_list = []
        host_info = []
        failed = False
        for key in hosts_processed:
            if hosts_processed[key]["status"] == "ERROR":
                exclude_list.append(key)
                logger.error(
                    "%s - unable to fetch cnc information from iDB. Check manually." % key)
                failed = True
            elif hosts_processed[key]["status"] == "SUCCESS":
                include_list.append(key)
                host_info.append(hosts_processed[key]["info"])

        logger.info("exclude: %s" % ','.join(exclude_list))
        logger.info("include: %s" % ','.join(include_list))
        logger.debug(host_info)
        misc.write_to_include_file(casenum, include_list)
        for e_host in exclude_list:
            misc.write_to_exclude_file(casenum, e_host, "iDBError")
        misc.write_to_hostinfo_file(casenum, host_info)
        misc.write_to_cnc_file(casenum, host_info)

    elif args.action == "routecheck":
        if not misc.check_file_exists(casenum, type="include"):
            logger.error("%s/%s_include file not found or inaccessible" %
                         (user_home, casenum))
            sys.exit(1)
        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadRouteCheck(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            queue.put(h)
        queue.join()

        include_list = []
        exclude_list = []
        failed = False

        for key in hosts_processed:
            if hosts_processed[key]["status"] == "ERROR":
                exclude_list.append(key)
                logger.error("%s - %s" % (key, hosts_processed[key]["info"]["error"]))
                failed = True
            elif hosts_processed[key]["status"] == "SUCCESS":
                include_list.append(key)
                logger.info("%s - %s" %
                            (key, hosts_processed[key]["info"]["success"]))

        logger.info("exclude: %s" % ','.join(exclude_list))
        logger.info("include: %s" % ','.join(include_list))
        misc.write_to_include_file(casenum, include_list)
        for e_host in exclude_list:
            misc.write_to_exclude_file(casenum, e_host, "BMCCheckFailed")
        if not len(include_list) > 0:
            logger.error("No hosts left for processing further. %s/%s_include file is empty after routecheck." %
                         (user_home, casenum))
            sys.exit(1)

    elif args.action == "image":
        if args.host_role:
            role = args.host_role
        else:
            role = None

        preserve = args.preserve_data
        disk_config = args.disk_config

        dry_run = args.no_op
        if not (misc.check_file_exists(casenum, type="include") and misc.check_file_exists(casenum, type="hostinfo")):
            logger.error("%s/%s_include/%s/%s_hostinfo file not found or inaccessible" %
                         (user_home, casenum, user_home, casenum))
            sys.exit(1)

        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadImaging(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            lst = [h, role, preserve, disk_config, dry_run]
            queue.put(lst)
        queue.join()
        failed = False
        for key in hosts_processed:
            if hosts_processed[key]["status"] == "ERROR":
                if "error" in hosts_processed[key]["info"].keys():
                    logger.error(hosts_processed[key]["info"]["error"])
                elif "message" in hosts_processed[key]["info"].keys():
                    logger.error(hosts_processed[key]["info"]["message"])
                logger.error("Error processing %s with %s command. Please troubleshoot." % (
                    key, args.action))
                failed = True
            else:
                if dry_run:
                    print(hosts_processed[key]["info"]["dry_run"])
                if not dry_run:
                    logger.info("%s command was successful on %s." % (args.action, key))
        if failed:
            sys.exit(1)

    elif args.action == "fail":
        dry_run = args.no_op
        if not (misc.check_file_exists(casenum, type="include") and misc.check_file_exists(casenum, type="hostinfo")):
            logger.error("%s/%s_include/%s/%s_hostinfo file not found or inaccessible" %
                         (user_home, casenum, user_home, casenum))
            sys.exit(1)

        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadFailHost(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            lst = [h, dry_run]
            queue.put(lst)
        queue.join()
        failed = False
        for key in hosts_processed:
            if hosts_processed[key]["status"] == "ERROR":
                if "error" in hosts_processed[key]["info"].keys():
                    logger.error(hosts_processed[key]["info"]["error"])
                elif "message" in hosts_processed[key]["info"].keys():
                    logger.error(hosts_processed[key]["info"]["message"])
                logger.error("Error processing %s with %s command. Please troubleshoot." % (
                    key, args.action))
                failed = True
            else:
                if dry_run:
                    print(hosts_processed[key]["info"]["dry_run"])
                if not dry_run:
                    logger.info("%s - %s" % (key, hosts_processed[key]["info"]["success"]))
                    logger.info("%s command was successful on %s." % (args.action, key))
        if failed:
            sys.exit(1)

    elif args.action == "rebuild":
        preserve = args.preserve_data
        disk_config = args.disk_config
        dry_run = args.no_op
        if not (misc.check_file_exists(casenum, type="include") and misc.check_file_exists(casenum, type="hostinfo")):
            logger.error("%s/%s_include/%s/%s_hostinfo file not found or inaccessible" %
                         (user_home, casenum, user_home, casenum))
            sys.exit(1)

        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadRebuilding(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            lst = [h, preserve, disk_config, dry_run]
            queue.put(lst)
        queue.join()
        failed = False
        for key in hosts_processed:
            if hosts_processed[key]["status"] == "ERROR":
                if "error" in hosts_processed[key]["info"].keys():
                    logger.error(hosts_processed[key]["info"]["error"])
                elif "message" in hosts_processed[key]["info"].keys():
                    logger.error(hosts_processed[key]["info"]["message"])
                logger.error("Error processing %s with %s command. Please troubleshoot." % (
                    key, args.action))
                failed = True
            else:
                if dry_run:
                    print(hosts_processed[key]["info"]["dry_run"])
                if not dry_run:
                    logger.info("%s - %s" % (key, hosts_processed[key]["info"]["success"]))
                    logger.info("%s command was successful on %s." % (args.action, key))
        if failed:
            sys.exit(1)

    elif args.action == "deploy":
        if not args.host_role:
            logger.error("please provide role with --role.")
            sys.exit(1)
        role = args.host_role
        if not args.cluster_name:
            logger.error("please provide cluster with --cluster.")
            sys.exit(1)
        cluster = args.cluster_name.upper()
        if not args.superpod_name:
            logger.error("please provide superpod with --superpod.")
            sys.exit(1)
        superpod = args.superpod_name.upper()
        preserve = args.preserve_data
        dry_run = args.no_op
        if not (misc.check_file_exists(casenum, type="include") and misc.check_file_exists(casenum, type="hostinfo")):
            logger.error("%s/%s_include/%s/%s_hostinfo file not found or inaccessible" %
                         (user_home, casenum, user_home, casenum))
            sys.exit(1)

        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadDeploy(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            lst = [h, role, cluster, superpod, preserve, dry_run]
            queue.put(lst)
        queue.join()
        failed = False
        for key in hosts_processed:
            if hosts_processed[key]["status"] == "ERROR":
                if "error" in hosts_processed[key]["info"].keys():
                    logger.error(hosts_processed[key]["info"]["error"])
                elif "message" in hosts_processed[key]["info"].keys():
                    logger.error(hosts_processed[key]["info"]["message"])
                logger.error("Error processing %s with %s command. Please troubleshoot." % (
                    key, args.action))
                failed = True
            else:
                if dry_run:
                    print(hosts_processed[key]["info"]["dry_run"])
                if not dry_run:
                    logger.info("%s - %s" % (key, hosts_processed[key]["info"]["success"]))
                    logger.info("%s command was successful on %s." % (args.action, key))
        if failed:
            sys.exit(1)

    elif args.action == "status":
        if not args.prev_action:
            logger.error(
                "please provide previous racktastic action performed using --previous.")
            sys.exit(1)
        delay = int(args.delay_in_mins) * 60
        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadStatusCheck(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            lst = [h, delay, args.prev_action]
            queue.put(lst)
        queue.join()
        failed = False
        expected_status = ""
        if args.prev_action in ["image", "rebuild"]:
            expected_status = "awaiting_deployment"
        elif args.prev_action == "deploy":
            expected_status = "deployed"
        elif args.prev_action == "fail":
            expected_status == "failed"
        for key in hosts_processed:
            if hosts_processed[key]["status"] == expected_status:
                logger.info("%s successfully processed. Latest status after %s command - %s" %
                            (key, args.prev_action, hosts_processed[key]["status"]))
            elif "message" in hosts_processed[key]["info"].keys():
                logger.error("%s command on %s - %s. Please troubleshoot." %
                             (args.prev_action, key, hosts_processed[key]["info"]["message"]))
                failed = True
            elif "error" in hosts_processed[key]["info"].keys():
                logger.error("%s command on %s - %s. Please troubleshoot." %
                             (args.prev_action, key, hosts_processed[key]["info"]["error"]))
                failed = True
        if failed:
            sys.exit(1)

    elif args.action == "erasehostname":
        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadEraseHostName(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            queue.put(h)
        queue.join()
        failed = False
        for key in hosts_processed:
            if hosts_processed[key]["status"] == "ERROR":
                logger.error("%s - %s" %
                             (key, hosts_processed[key]["info"]["error"]))
                failed = True
            else:
                logger.info("%s - %s" %
                            (key, hosts_processed[key]["info"]["success"]))
                logger.info("%s command was successful on %s." %
                            (args.action, key))
        if failed:
            sys.exit(1)

    elif args.action == "updateopsstatus":
        if not args.idb_status:
            logger.error("please provide a valid iDB status using --status.")
            sys.exit(1)
        idb_status = str(args.idb_status).upper()
        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadUpdateOpsStatus(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            lst = [h, idb_status]
            queue.put(lst)
        queue.join()
        failed = False
        for key in hosts_processed:
            if hosts_processed[key]["status"] == "ERROR":
                logger.error("%s - %s" %
                             (key, hosts_processed[key]["info"]["error"]))
                failed = True
            else:
                logger.info("%s - %s" %
                            (key, hosts_processed[key]["info"]["success"]))
                logger.info("%s command was successful on %s." %
                            (args.action, key))
        if failed:
            sys.exit(1)

    elif args.action == "idb_check":
        if not args.idb_status:
            logger.error("please provide a valid iDB status using --status.")
            sys.exit(1)
        idb_status = str(args.idb_status).upper()
        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadCheckIdbStatus(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            lst = [h, idb_status]
            queue.put(lst)
        queue.join()
        failed = False
        for key in hosts_processed:
            if hosts_processed[key]["status"] == "ERROR":
                logger.error("%s - %s" % (key, hosts_processed[key]["info"]["error"]))
                failed = True
            else:
                logger.info("%s - %s" % (key, hosts_processed[key]["info"]["success"]))
                logger.info("%s command was successful on %s." % (args.action, key))
        if failed:
            sys.exit(1)

    elif args.action == "check_disk_config":
        if not misc.check_file_exists(casenum, type="include"):
            logger.error("%s/%s_include file not found or inaccessible" %
                         (user_home, casenum))
            sys.exit(1)

        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadDiskConfigCheck(queue, casenum, hosts_processed, args.disk_config)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            queue.put(h)
        queue.join()

        include_list = []
        exclude_list = []
        failed = False

        for key in hosts_processed:
            if hosts_processed[key]["status"] == "ERROR":
                exclude_list.append(key)
                logger.error("%s - %s" % (key, hosts_processed[key]["info"]["error"]))
                failed = True
            elif hosts_processed[key]["status"] == "SUCCESS":
                include_list.append(key)
                logger.info("%s - %s" %
                            (key, hosts_processed[key]["info"]["success"]))

        logger.info("exclude: %s" % ','.join(exclude_list))
        logger.info("include: %s" % ','.join(include_list))
        misc.write_to_include_file(casenum, include_list)
        for e_host in exclude_list:
            misc.write_to_exclude_file(casenum, e_host, "DiskConfigMisMatch\n")

    elif args.action == "validate_nic":
        if not misc.check_file_exists(casenum, type="include"):
            logger.error("%s/%s_include file not found or inaccessible" % (user_home, casenum))
            sys.exit(1)
        if not misc.check_file_exists(casenum, type="macinfo"):
            logger.error("%s/%s_macinfo file not found or inaccessible" % (user_home, casenum))
            sys.exit(1)

        mac_info_file = open("%s/%s_macinfo" % (user_home, casenum), "r")
        mac_info = json.load(mac_info_file)

        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadValidateNic(queue, casenum, hosts_processed, mac_info)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            queue.put(h)
        queue.join()

        include_list = []
        exclude_list = []

        for key in hosts_processed:
            if hosts_processed[key]["status"] == "ERROR":
                exclude_list.append(key)
                logger.error("%s - %s" % (key, hosts_processed[key]["info"]["error"]))
            elif hosts_processed[key]["status"] == "SUCCESS":
                include_list.append(key)
                logger.info("%s - %s" % (key, hosts_processed[key]["info"]["success"]))

        logger.info("exclude: %s" % ','.join(exclude_list))
        logger.info("include: %s" % ','.join(include_list))
        for e_host in exclude_list:
            misc.write_to_exclude_file(casenum, e_host, "MACAddrMisMatch\n")
        if not include_list:
            logger.error("No hosts left to process after this step")
            sys.exit(1)


if __name__ == "__main__":
    logger = logging.getLogger()
    main()
