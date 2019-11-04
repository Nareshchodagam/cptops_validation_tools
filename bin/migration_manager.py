#!/usr/bin/python

from argparse import ArgumentParser
import logging
from os import path
from subprocess import call, Popen, PIPE, CalledProcessError
import sys
import threading
import Queue
import json
import time


class Util:
    def __init__(self):
        self.user_home = path.expanduser("~")

    def has_valid_kerberos_ticket(self):
        return True if call(['klist', '-s']) == 0 else False
    
    def ask_user(self):
        check = str(raw_input("Do you want to proceed with the execution? (y/n) ")).strip().lower()
        try:
            if check[0] == "y":
                return True
            elif check[0] == "n":
                return False
            else:
                print("Please enter y or n.")
                return self.ask_user()
        except Exception as error:
            print("Please enter valid input")
            logger.error(error)
            return self.ask_user()

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
            logging.info("%s - Retry #%s fetching host cnc information from iDB as it's failed in previous attempt" % (h, (count+1)))
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
        host, role, preserve, disk_config = self.queue.get()
        max_retries = 2
        count = 0
        logger.info("Triggering image command on %s. Will be retrying for a maximum of %s times if failed" % (host, max_retries))
        result, status = self.mig.trigger_image(host, self.casenum, role=role, preserve=preserve, disk_config=disk_config)
        while status == "ERROR" and "error" in result.keys() and count != max_retries:
            logging.info("Retry #%s image command on %s as it's failed in previous attempt" % (count, host))
            result, status = self.mig.trigger_image(host, self.casenum, role=role, preserve=preserve, disk_config=disk_config)
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
        host, preserve, disk_config = self.queue.get()
        max_retries = 2
        count = 0
        logger.info("Triggering rebuild_failed_host command on %s. Will be retrying for a maximum of %s times if failed" % (host, max_retries))
        result, status = self.mig.rebuild_failed_host(host, self.casenum, preserve=preserve, disk_config=disk_config)
        while status == "ERROR" and "error" in result.keys() and count != max_retries:
            logging.info("Retry #%s rebuild_failed_host command on %s as it's failed in previous attempt" % (count, host))
            result, status = self.mig.rebuild_failed_host(host, self.casenum, preserve=preserve, disk_config=disk_config)
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
        host, role, cluster, superpod, preserve = self.queue.get()
        result, status = self.mig.trigger_deploy(host, self.casenum, role=role, cluster=cluster, superpod=superpod, preserve=preserve)
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
        host = self.queue.get()
        result, status = self.mig.update_idb_status(host, self.casenum)
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
        host, delay = self.queue.get()
        result, status = self.mig.check_status(host, self.casenum, delay)
        self.hosts_processed[host] = {"info": result, "status": status}
        self.queue.task_done()


class Migration:
    def __init__(self):
        self.user_home = path.expanduser("~")

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
            ci_dict = json.loads(self.exec_cmd("inventory-action.pl -q -use_krb_auth -resource hostconfig -action read -host.name " + hostname + " -fields key,value -key apiUrl"))
            sn_dict = json.loads(self.exec_cmd("inventory-action.pl -q -use_krb_auth -resource host -action read -name " + hostname + " -fields serialNumber"))
            rp_dict = json.loads(self.exec_cmd("inventory-action.pl -q -use_krb_auth -resource hostconfig -action read -host.name " + hostname + " -fields key,value -key rackUPos"))
            cc_dict = json.loads(self.exec_cmd("inventory-action.pl -q -use_krb_auth -resource host -action read -host.name " + hostname + " -fields cluster.clusterConfigs.value,cluster.clusterConfigs.type"))
            sm_dict = json.loads(self.exec_cmd("inventory-action.pl -q -use_krb_auth -resource host -action read -host.name " + hostname + " -fields manufacturer"))
            logger.info("Got info for %s from iDB" % hostname)
            cnc_api_url = str(ci_dict["data"][0]["value"])
            serial_number = str(sn_dict["data"][0]["serialNumber"])
            rack_position = str(rp_dict["data"][0]["value"])
            manufacturer = str(sm_dict["data"][0]["manufacturer"])
            network_domain = "ops.sfdc.net"
            cluster_configs_list = list(cc_dict["data"][0]["cluster"]["clusterConfigs"])
            for i in cluster_configs_list:
                if "network-domain" in i.values():
                    network_domain = i["value"]
                    if network_domain == None or network_domain == "":
                        network_domain = "ops.sfdc.net"
            output.setdefault(str(hostname), {"cnc_api_url": cnc_api_url, "serial_number": serial_number, "rack_position": rack_position, "network_domain": network_domain, "manufacturer": manufacturer, "event": None})
            status = "SUCCESS"
        except ValueError:
            logger.debug("Error: unable to find racktastic apiUrl/serialNumber of %s in iDB" % hostname)
            output.setdefault(str(hostname), {"cnc_api_url": None, "serial_number": None, "rack_position": None, "network_domain": None, "manufacturer": None, "event": None})
            status = "ERROR"
        except:
            logger.debug("Error: unable to find racktastic apiUrl/serialNumber of %s in iDB" % hostname)
            output.setdefault(str(hostname), {"cnc_api_url": None, "serial_number": None, "rack_position": None, "network_domain": None, "manufacturer": None, "event": None})
            status = "ERROR"
        return output, status

    def route_check(self, hostname, casenum):
        """
        For a given host, this method checks if the host is reachable via ssh from within cnc
        """
        host_info_file = "%s/%s_hostinfo" % (self.user_home, casenum)
        try:
            f = open(host_info_file, "r")
        except IOError:
            logger.error("%s is not found or inaccessible" % host_info_file)
        host_info_dict = json.load(f)
        cnc_api_url = ""
        rack_position = ""
        output = {}
        status = {}

        for item in host_info_dict:
            if hostname in item.keys():
                cnc_api_url = item.values()[0]["cnc_api_url"]
                rack_position = item.values()[0]["rack_position"]
                break
        
        cnc_host = cnc_api_url.split("//")[1].split(":")[0]
        rack_ip = "192.168.1.%s" % rack_position
        ssh_opts = "-o LogLevel=QUIET -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        self.exec_cmd("scp %s /opt/cpt/bin/rack_port_check.py %s:%s/rack_port_check.py" % (ssh_opts, cnc_host, self.user_home))
        ssh_cmd = "ssh -4 -t %s %s \"python %s/rack_port_check.py --host %s\"" % (ssh_opts, cnc_host, self.user_home, rack_ip)
        try:
            ssh_out = self.exec_cmd(ssh_cmd)
            out = ssh_out.rstrip()
            if out == "open":
                output.setdefault("success", "%s - port 22 is open" % hostname)
                status = "SUCCESS"
            else:
                output.setdefault("error", "%s - no route to host" % hostname)
                status = "ERROR"
        except:
            output.setdefault("error", "%s - an error occured while processing the request on %s" % (hostname, cnc_host))
            status = "ERROR"
        self.exec_cmd("reset")
        return output, status

    def trigger_image(self, hostname, casenum, role="", preserve=False, disk_config=""):
        """
        For a given host this method triggers image event on cnc api url and validates whether that event successfully completed or not
        """
        host_info_file = "%s/%s_hostinfo" % (self.user_home, casenum)
        try:
            f = open(host_info_file, "r")
        except IOError:
            logger.error("%s is not found or inaccessible" % host_info_file)
        host_info_dict = json.load(f)
        cnc_api_url = ""
        serial_number = ""
        output = {}
        status = None
        for item in host_info_dict:
            if hostname in item.keys():
                cnc_api_url = item.values()[0]["cnc_api_url"]
                serial_number = item.values()[0]["serial_number"]
                break
        
        rack_status = self.check_rack_status(cnc_api_url)
        if not rack_status in ["ready"]:
            output.setdefault("error", "The rack status does not match it's expected state: 'ready' <> '%s'. Exiting." % rack_status)
            return output, "ERROR"
        else:
            image_cmd = "curl -s --request POST %sevent -d '{\"type\":\"image\",\"serial_number\":\"%s\",\"message\":{\"name\":\"vanilla\",\"preserve\":\"%s\",\"host_role\":\"%s\",\"disk_config\":\"%s\"}}'" % (cnc_api_url, serial_number, str(preserve).lower(), role, disk_config)
            logger.info("Image command - %s", image_cmd)
            image_cmd_response = json.loads(self.exec_cmd(image_cmd))
            if "error" in image_cmd_response.keys():
                output.setdefault("error", image_cmd_response["error"])
                status = "ERROR"
            else:
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
                        output.setdefault("success", "%s command %s processing on %s" % (event_type, e_status, hostname))
                    elif e_status == "failed":
                        status = "ERROR"
                        output.setdefault("error", "%s to process %s command on %s due to some error. \nCNC Host - %s\nSerial Number - %s" % (e_status, event_type, hostname, cnc_host, serial_number))
                else:
                    status = "ERROR"
                    output.setdefault("message", "%s command not processed within time on %s. \nCheck manually at %s" % (event_type, hostname, event_api_url))
        return output, status

    def rebuild_failed_host(self, hostname, casenum, preserve=False, disk_config=""):
        """
        For a given host that has racktastic status as failed, this method triggers rebuild_failed_host event of cnc api url and validates whether that successfully completed or not
        """
        host_info_file = "%s/%s_hostinfo" % (self.user_home, casenum)
        try:
            f = open(host_info_file, "r")
        except IOError:
            logger.error("%s is not found or inaccessible" % host_info_file)
        host_info_dict = json.load(f)
        cnc_api_url = ""
        serial_number = ""
        output = {}
        status = None

        for item in host_info_dict:
            if hostname in item.keys():
                cnc_api_url = item.values()[0]["cnc_api_url"]
                serial_number = item.values()[0]["serial_number"]
                break
        
        rack_status = self.check_rack_status(cnc_api_url)
        if not rack_status in ["ready"]:
            output.setdefault("error", "The rack status does not match it's expected state: 'ready' <> '%s'. Exiting." % rack_status)
            return output, "ERROR"
        else:
            rebuild_cmd = "curl -s --request POST %sevent -d '{\"type\":\"rebuild_failed_host\",\"serial_number\":\"%s\",\"message\":{\"name\":\"vanilla\",\"preserve\":\"%s\",\"disk_config\":\"%s\"}}'" % (cnc_api_url, serial_number, str(preserve).lower(), disk_config)
            logger.info("rebuild command - %s ", rebuild_cmd)
            rebuild_cmd_response = json.loads(self.exec_cmd(rebuild_cmd))
            if "error" in rebuild_cmd_response.keys():
                output.setdefault("error", rebuild_cmd_response["error"])
                status = "ERROR"
            else:
                cnc_host = cnc_api_url.split("//")[1].split(".")[0]
                event_type = rebuild_cmd_response["type"]
                event_id = rebuild_cmd_response["id"]
                event_status = rebuild_cmd_response["status"]
                logger.info("%s - [%s] %s -- %s" % (hostname, event_id, event_type, event_status))
                event_api_url = "%sevent/%s" % (cnc_api_url, event_id)
                e_result, e_status = self.check_event_status(event_api_url)
                logger.info("%s - %s" % (hostname, e_status))
                if e_result == True:
                    if e_status == "completed":
                        status = "SUCCESS"
                        output.setdefault("success", "%s command %s processing on %s" % (event_type, e_status, hostname))
                    elif e_status == "failed":
                        status = "ERROR"
                        output.setdefault("error", "%s to process %s command on %s due to some error. \nCNC Host - %s\nSerial Number - %s" % (e_status, event_type, hostname, cnc_host, serial_number))
                else:
                    status = "ERROR"
                    output.setdefault("message", "%s command not processed within time on %s. \nCheck manually at %s" % (event_type, hostname, event_api_url))
        return output, status

    def trigger_deploy(self, hostname, casenum, role="", cluster="", superpod="", preserve=False):
        """
        For a given host, this method triggers deploy event on cnc api url and validates whether it is completed or not.
        """
        host_info_file = "%s/%s_hostinfo" % (self.user_home, casenum)
        try:
            f = open(host_info_file, "r")
        except IOError:
            logger.error("%s is not found or inaccessible" % host_info_file)
        host_info_dict = json.load(f)
        cnc_api_url = ""
        serial_number = ""
        network_domain = ""
        output = {}
        status = None

        for item in host_info_dict:
            if hostname in item.keys():
                cnc_api_url = item.values()[0]["cnc_api_url"]
                serial_number = item.values()[0]["serial_number"]
                network_domain = item.values()[0]["network_domain"]
                break

        host_fqdn = "%s.%s" % (hostname, network_domain)
        rack_status = self.check_rack_status(cnc_api_url)
        if not rack_status in ["ready"]:
            output.setdefault("error", "The rack status does not match it's expected state: 'ready' <> '%s'. Exiting." % rack_status)
            return output, "ERROR"
        else:
            deploy_cmd = "curl -s --request POST %sevent -d '{\"type\":\"deploy\",\"serial_number\":\"%s\",\"message\":{\"inventory_idb_cluster_name\":\"%s\",\"inventory_idb_superpod_name\":\"%s\",\"default_hostname\":\"%s\",\"host_role\":\"%s\", \"preserve\":\"%s\"}}'" % (cnc_api_url, serial_number, cluster, superpod, host_fqdn, role, str(preserve).lower())
            logger.info("Deploy command - %s", deploy_cmd)
            deploy_cmd_response = json.loads(self.exec_cmd(deploy_cmd))
            if "error" in deploy_cmd_response.keys():
                output.setdefault("error", deploy_cmd_response["error"])
                status = "ERROR"
            else:
                cnc_host = cnc_api_url.split("//")[1].split(".")[0]
                event_type = deploy_cmd_response["type"]
                event_id = deploy_cmd_response["id"]
                event_status = deploy_cmd_response["status"]
                logger.info("%s - [%s] %s -- %s" % (hostname, event_id, event_type, event_status))
                event_api_url = "%sevent/%s" % (cnc_api_url, event_id)
                e_result, e_status = self.check_event_status(event_api_url)
                logger.info("%s - %s" % (hostname, e_status))
                if e_result == True:
                    if e_status == "completed":
                        status = "SUCCESS"
                        output.setdefault("success", "%s command %s processing on %s" % (event_type, e_status, hostname))
                    elif e_status == "failed":
                        status = "ERROR"
                        output.setdefault("error", "%s to process %s command on %s due to some error. \nCNC Host - %s\nSerial Number - %s" % (e_status, event_type, hostname, cnc_host, serial_number))
                else:
                    status = "ERROR"
                    output.setdefault("message", "%s command not processed within time on %s. \nCheck manually at %s" % (event_type, hostname, event_api_url))
        return output, status
    
    def erase_hostname(self, hostname, casenum):
        """
        For a given host, this method erases the hostname in iDB in order to deploy
        """
        host_info_file = "%s/%s_hostinfo" % (self.user_home, casenum)
        try:
            f = open(host_info_file, "r")
        except IOError:
            logger.error("%s is not found or inaccessible" % host_info_file)
        host_info_dict = json.load(f)
        serial_number = ""
        
        output = {}
        status = None
        for item in host_info_dict:
            if hostname in item.keys():
                serial_number = item.values()[0]["serial_number"]
                break
        hname = ""
        verify_cmd = "inventory-action.pl -q -use_krb_auth -resource host -action read -serialNumber %s -fields name" % serial_number
        try:
            verify_cmd_response = json.loads(self.exec_cmd(verify_cmd))
            hname = verify_cmd_response["data"][0]["name"]
        except ValueError:
            # handles the null values if iDB returns empty
            hname == ""
        if hname == None:
            output.setdefault("success", "hostname is already null in iDB for host %s" % hostname)
            status = "SUCCESS"
        else:
            try:
                erase_cmd = "inventory-action.pl -q -use_krb_auth -resource host -action update -serialNumber %s -updateFields \"name=null\"" % serial_number
                self.exec_cmd(erase_cmd)
                logger.debug("%s - payload sent to erase" % hostname)
                verify_cmd2_response = json.loads(self.exec_cmd(verify_cmd))
                if verify_cmd2_response["data"][0]["name"] == None:
                    output.setdefault("success", "%s hostname erased successfully" % hostname)
                    status = "SUCCESS"
                else:
                    output.setdefault("error", "unable to erase hostname for %s due to some error" % hostname)
                    status = "ERROR"
            except:
                output.setdefault("error", "%s - an error occured while processing the request" % hostname)
                status = "ERROR"
        return output, status

    def update_idb_status(self, hostname, casenum):
        """
        For a given host, this method updates the iDB status to ACTIVE given that the host is in PROVISIONING status
        """
        host_info_file = "%s/%s_hostinfo" % (self.user_home, casenum)
        try:
            f = open(host_info_file, "r")
        except IOError:
            logger.error("%s is not found or inaccessible" % host_info_file)
        host_info_dict = json.load(f)
        serial_number = ""
        output = {}
        status = None
        for item in host_info_dict:
            if hostname in item.keys():
                serial_number = item.values()[0]["serial_number"]
                break
        max_retries = 30
        interval = 60
        count = 0
        old_status = ""
        old_status_cmd = "inventory-action.pl -q -use_krb_auth -resource host -action read -serialNumber %s -fields operationalStatus" % serial_number
        while old_status != "PROVISIONING":
            if count == max_retries:
                output.setdefault("message","iDB status was not changed by puppet to PROVISIONING with in time. Please retry/check manually.")
                status = "ERROR"
                break
            try:
                old_status_cmd_response = json.loads(self.exec_cmd(old_status_cmd))
                old_status = old_status_cmd_response["data"][0]["operationalStatus"]
            except ValueError:
                # handles the null values if iDB returns empty
                old_status = ""
            if old_status == "PROVISIONING":
                logger.info("%s iDB status matched with desired status 'PROVISIONING' <> '%s'" % (hostname, old_status))
                break
            if old_status == "ACTIVE":
                output.setdefault("success", "%s iDB status is already '%s'. Cross-verify the host manually." % (hostname, old_status))
                status = "SUCCESS"
                return output, status
            logger.info("%s - iDB status does not match desired status 'PROVISIONING' <> '%s'" % (hostname, old_status))
            logger.info("Retrying in %s seconds" % interval)
            time.sleep(interval)
            count += 1
        try:
            update_cmd = "inventory-action.pl -q -use_krb_auth -resource host -action update -serialNumber %s -updateFields \"operationalStatus=ACTIVE\"" % serial_number
            self.exec_cmd(update_cmd)
            logger.debug("%s - payload sent to update iDB status to ACTIVE" % hostname)
            new_status = json.loads(self.exec_cmd(old_status_cmd))["data"][0]["operationalStatus"]
            if new_status == "ACTIVE":
                output.setdefault("success", "%s - iDB status successfully updated to %s" % (hostname, new_status))
                status = "SUCCESS"
            else:
                output.setdefault("error", "%s - failed to change iDB Status to 'ACTIVE' <> '%s'" % (hostname, new_status))
                status = "ERROR"
        except:
            output.setdefault("error", "%s - an error occurred while processing the request" % hostname)
        return output, status

    def check_status(self, hostname, casenum, delay):
        """
        For a given host, this method checks for the status changes in racktastic
        """
        host_info_file = "%s/%s_hostinfo" % (self.user_home, casenum)
        try:
            f = open(host_info_file, "r")
        except IOError:
            logger.error("%s is not found or inaccessible" % host_info_file)
        host_info_dict = json.load(f)
        cnc_api_url = ""
        serial_number = ""
        output = {}
        for item in host_info_dict:
            if hostname in item.keys():
                cnc_api_url = item.values()[0]["cnc_api_url"]
                serial_number = item.values()[0]["serial_number"]
                break
            
        logger.info("%s - %s, %s" % (hostname, serial_number, cnc_api_url))
        rack_status = self.check_rack_status(cnc_api_url)
        if not rack_status in ["ready"]:
            output.setdefault("error", "The rack status does not match it's expected state: 'ready' <> '%s'. Exiting." % rack_status)
            return output, "Rack - %s" % rack_status
        else:
            poll_interval = 60
            retry_count = 60
            count = 0
            result = False
            status = None
            logger.info("Pausing %s seconds for the status to change" % delay)
            time.sleep(delay)
            while result != True:
                status_cmd = "curl -s --request GET %shost/%s" % (cnc_api_url, serial_number)
                status_cmd_response = json.loads(self.exec_cmd(status_cmd))
                status = status_cmd_response["state"]
                logger.info("%s - %s" % (hostname, status))
                if status in ["awaiting_deployment", "deployed"]:
                    result = True
                    output.setdefault("success", "%s processed successfully. latest status - %s" % (hostname, status))
                    break
                logger.info("Retrying in %s seconds " % (poll_interval))
                time.sleep(poll_interval)
                count += 1
                if count == retry_count:
                    logger.info("%s status didn't change in expected time. Please retry" % hostname)
                    output.setdefault("message", "unable to process %s in time." % hostname)
                    result = False
                    break
            return output, status
    
    def check_event_status(self, event_api_url):
        delay = 60
        poll_interval = 30
        retry_count = 60
        count = 0
        result = False
        status = None
        logger.info("Pausing %s seconds for the event status to change" % delay)
        time.sleep(delay)
        while result != True:
            status = json.loads(self.exec_cmd("curl -s --request GET %s" % event_api_url))["status"]
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
        return result, status

    def check_rack_status(self, cnc_api_url):
        cnc_host = cnc_api_url.split("//")[1].split(".")[0]
        rack_stat_cmd = "curl -s --connect-timeout 10 --request GET " + cnc_api_url + "status"
        try:
            rack_stat = json.loads(self.exec_cmd(rack_stat_cmd))
            rack_status = rack_stat["rack"]["state"]
            logger.debug("Rack Status of %s - %s" % (cnc_host, rack_status))
            return rack_status
        except:
            logger.error("The rack status of %s could not be fetched in time. Exiting." % cnc_host)
            return "timed out"


def main():
    """
    This is main method which will accept the command line argument and pass to the class methods.
    """

    parser = ArgumentParser(prog='migration_manager.py', usage="\n %(prog)s \n\t-h --help prints this help \n\t-v verbose output \n\t-c casenum -a cncinfo \n\t-c casenum -a routecheck \n\t-c casenum -a image --role <ROLE> [--preserve] [--disk_config <default is stage1v0>] \n\t-c casenum -a delpoy --role <ROLE> --cluster <CLUSTER> --superpod <SUPERPOD> [--preserve] \n\t-c casenum -a rebuild [--preserve] [--disk_config <default is stage1v0>] \n\t-c casenum -a status --delay <MINS>\n\t-c casenum -a erasehostname \n\t-c casenum -a updateopsstatus")
    
    parser.add_argument("-c", dest="case", help="case number", required=True)
    parser.add_argument("-a", dest="action", help="specify intended action", required=True, choices=["cncinfo", "routecheck", "image", "deploy", "rebuild", "status", "erasehostname", "updateopsstatus"])
    parser.add_argument("--role", dest="host_role", help="specify host role")
    parser.add_argument("--cluster", dest="cluster_name", help="specify cluster name")
    parser.add_argument("--superpod", dest="superpod_name", help="specify super pod name")
    parser.add_argument("--disk_config", dest="disk_config", help="specify disk config e.g stage1v0|fastcache2", default="stage1v0")
    parser.add_argument("--preserve", dest="preserve_data", action="store_true", help="include this to preserve data", default=False)
    parser.add_argument("--delay", dest="delay_in_mins", type=int, default=10, help="specify delay in minutes")
    parser.add_argument("-v", dest="verbose", action="store_true", help="verbose output", default=False)

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
    thread_count = len(host_list) # number of parallel threads 

    if args.action == "cncinfo":
        if not misc.check_file_exists(casenum, type="include"):
            logger.error("%s/%s_include file not found or inaccessible" % (user_home, casenum))
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
                logger.error("%s - unable to fetch cnc information from iDB. Check manually." % key)
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

        if failed:
            if not misc.ask_user():
                sys.exit(1)

    elif args.action == "routecheck":
        if not misc.check_file_exists(casenum, type="include"):
            logger.error("%s/%s_include file not found or inaccessible" % (user_home, casenum))
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
                logger.error("%s - no route to host from cnc." % key)
                failed = True
            elif hosts_processed[key]["status"] == "SUCCESS":
                include_list.append(key)
                logger.info("%s - %s" % (key, hosts_processed[key]["info"]["success"]))
        
        logger.info("exclude: %s" % ','.join(exclude_list))
        logger.info("include: %s" % ','.join(include_list))
        misc.write_to_include_file(casenum, include_list)
        for e_host in exclude_list:
            misc.write_to_exclude_file(casenum, e_host, "NoRouteToHost")
        
        if failed:
            if not misc.ask_user():
                sys.exit(1)

    elif args.action == "image":
        if not args.host_role:
            logger.error("please provide role with --role.")
            sys.exit(1)
        role = args.host_role
        preserve = args.preserve_data
        disk_config = args.disk_config
        if not (misc.check_file_exists(casenum, type="include") and misc.check_file_exists(casenum, type="hostinfo")):
            logger.error("%s/%s_include/%s/%s_hostinfo file not found or inaccessible" % (user_home, casenum, user_home, casenum))
            sys.exit(1)

        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadImaging(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            lst = [h, role, preserve, disk_config]
            queue.put(lst)
        queue.join()
        failed = False
        for key in hosts_processed:
            if hosts_processed[key]["status"] == "ERROR":
                if "error" in hosts_processed[key]["info"].keys():
                    logger.error(hosts_processed[key]["info"]["error"])
                elif "message" in hosts_processed[key]["info"].keys():
                    logger.error(hosts_processed[key]["info"]["message"])
                logger.error("Error processing %s with %s command. Please troubleshoot." % (key, args.action))
                failed = True
            else:
                logger.info("%s command was successful on %s." % (args.action, key))
        if failed:
            sys.exit(1)

    elif args.action == "rebuild":
        preserve = args.preserve_data
        disk_config = args.disk_config
        if not (misc.check_file_exists(casenum, type="include") and misc.check_file_exists(casenum, type="hostinfo")):
            logger.error("%s/%s_include/%s/%s_hostinfo file not found or inaccessible" % (user_home, casenum, user_home, casenum))
            sys.exit(1)
        
        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadRebuilding(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            lst = [h, preserve, disk_config]
            queue.put(lst)
        queue.join()
        failed = False
        for key in hosts_processed:
            if hosts_processed[key]["status"] == "ERROR":
                if "error" in hosts_processed[key]["info"].keys():
                    logger.error(hosts_processed[key]["info"]["error"])
                elif "message" in hosts_processed[key]["info"].keys():
                    logger.error(hosts_processed[key]["info"]["message"])
                logger.error("Error processing %s with %s command. Please troubleshoot." % (key, args.action))
                failed = True
            else:
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
        if not (misc.check_file_exists(casenum, type="include") and misc.check_file_exists(casenum, type="hostinfo")):
            logger.error("%s/%s_include/%s/%s_hostinfo file not found or inaccessible" % (user_home, casenum, user_home, casenum))
            sys.exit(1)
        
        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadDeploy(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            lst = [h, role, cluster, superpod, preserve]
            queue.put(lst)
        queue.join()
        failed = False
        for key in hosts_processed:
            if hosts_processed[key]["status"] == "ERROR":
                if "error" in hosts_processed[key]["info"].keys():
                    logger.error(hosts_processed[key]["info"]["error"])
                elif "message" in hosts_processed[key]["info"].keys():
                    logger.error(hosts_processed[key]["info"]["message"])
                logger.error("Error processing %s with %s command. Please troubleshoot." % (key, args.action))
                failed = True
            else:
                logger.info("%s - %s" % (key, hosts_processed[key]["info"]["success"]))
                logger.info("%s command was successful on %s." % (args.action, key))
        if failed:
            sys.exit(1)
    
    elif args.action == "status":
        delay = int(args.delay_in_mins) * 60
        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadStatusCheck(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            lst = [h, delay]
            queue.put(lst)
        queue.join()
        failed = False
        for key in hosts_processed:
            if hosts_processed[key]["status"] in ["awaiting_deployment", "deployed"]:
                logger.info("%s successfully processed. Latest status - %s"% (key, hosts_processed[key]["status"]))
            elif "message" in hosts_processed[key]["info"].keys():
                logger.error("%s - %s. Please troubleshoot." % (key, hosts_processed[key]["info"]["message"]))
                failed = True
            else:
                logger.error("%s - %s. Please troubleshoot." % (key, hosts_processed[key]["info"]["error"]))
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
                logger.error("%s - %s" % (key, hosts_processed[key]["info"]["error"]))
                failed = True
            else:
                logger.info("%s - %s" % (key, hosts_processed[key]["info"]["success"]))
                logger.info("%s command was successful on %s." % (args.action, key))
        if failed:
            sys.exit(1)
        
    elif args.action == "updateopsstatus":
        hosts_processed = {}
        queue = Queue.Queue()
        for i in range(thread_count):
            t = ThreadUpdateOpsStatus(queue, casenum, hosts_processed)
            t.setDaemon(True)
            t.start()
        for h in host_list:
            queue.put(h)
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

if __name__ == "__main__":
    logger = logging.getLogger()
    main()
