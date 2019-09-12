#!/usr/bin/python

import sys
from argparse import ArgumentParser
import logging
import json
import time
import threading
import Queue
from StringIO import StringIO
from multiprocessing import Pool
import subprocess
from subprocess import Popen, PIPE, CalledProcessError
from functools import partial
import copy_reg
import types
from os import path

# code to support calling instance methods in multiprocessing in python2


def _reduce_method(m):
    if m.im_self is None:
        return getattr, (m.im_class, m.im_func.func_name)
    else:
        return getattr, (m.im_self, m.im_func.func_name)


copy_reg.pickle(types.MethodType, _reduce_method)


class ThreadHosts(threading.Thread):
    """using Threads and Queues to keep polling racktasting api url for status changes"""
    def __init__(self, queue, casenum, hosts_completed):
        threading.Thread.__init__(self)
        self.queue = queue
        self.casenum = casenum
        self.hosts_completed = hosts_completed
        mig = Migration()

    def run(self):
        while True:
            host, case, ncount = self.queue.get()
            result, status = mig.check_status(host, casenum=case)
            logger.debug(host + " - " + status)
            if result == False:
                self.queue.task_done()
                self.hosts_completed[host] = status
                break
            self.hosts_completed[host] = status
            self.queue.task_done()


class ImageStatusThreads(threading.Thread):

    def __init__(self, queue, processed_hosts):
        threading.Thread.__init__(self)
        self.queue = queue
        self.processed_hosts = processed_hosts
        mig = Migration()

    def run(self):
        while True:
            host, url, ncount = self.queue.get()
            result, status = mig.check_event_status(host, url=url)
            logger.debug(host + " - " + status)
            if result == False:
                self.queue.task_done()
                self.processed_hosts[host] = status
                break
            self.processed_hosts[host] = status
            self.queue.task_done()


class Migration:
    
    def __init__(self):
        self.user_home = path.expanduser('~')

    def has_valid_kerb_ticket(self):
        return True if subprocess.call(['klist', '-s']) == 0 else False

    def update_ops_status(self, hostname, casenum=""):
        try:
            cnc_file = open(self.user_home + "/" + casenum + "_hostinfo", "r")
        except IOError:
            logger.error(casenum + "_hostinfo is missing/inaccessible")
        cnc_json = json.load(cnc_file)
        for o in cnc_json:
            if hostname in o.keys():
                serial_number = str(o.values()[0][0]["serial_number"])
                break
        
        count = 0
        old_stat = str(json.loads(self.exec_cmd("inventory-action.pl -q -use_krb_auth -resource host -action read -serialNumber " + serial_number + " -fields operationalStatus"))["data"][0]["operationalStatus"])
        while old_stat != "PROVISIONING":
            if count == 40:
                logger.info("iDB status was not changed by puppet to PROVISIONING with in time. Please retry/check manually.")
                return old_stat
            logger.info("iDB status for %s don't match desired status - 'PROVISIONING' <> '%s'. retring after 30 seconds" % (hostname, old_stat))
            time.sleep(30)
            old_stat = str(json.loads(self.exec_cmd("inventory-action.pl -q -use_krb_auth -resource host -action read -serialNumber " + serial_number + " -fields operationalStatus"))["data"][0]["operationalStatus"])
            if old_stat == "PROVISIONING":
                logger.info("iDB status for %s matched desired status - 'PROVISIONING' <> '%s'" % (hostname, old_stat))
                break
            count += 1

        stat_dict = "inventory-action.pl -q -use_krb_auth -resource host -action update -serialNumber " + serial_number + " -updateFields \"operationalStatus=ACTIVE\""
        self.exec_cmd(stat_dict)

        check = json.loads(self.exec_cmd("inventory-action.pl -q -use_krb_auth -resource host -action read -serialNumber " + serial_number + " -fields operationalStatus"))
        opstat = str(check["data"][0]["operationalStatus"])
        if opstat == "ACTIVE":
            return True
        return opstat

    def erase_hostname(self, hostname, casenum=""):
        try:
            cnc_file = open(self.user_home + "/" + casenum + "_hostinfo", "r")
        except IOError:
            logger.error(casenum + "_hostinfo is missing/inaccessible")
        cnc_json = json.load(cnc_file)
        for o in cnc_json:
            if hostname in o.keys():
                serial_number = str(o.values()[0][0]["serial_number"])
                break

        hn_verify = "inventory-action.pl -q -use_krb_auth -resource host -action read -serialNumber " + serial_number + " -fields name"
        verify = json.loads(self.exec_cmd(hn_verify))
        hn = verify["data"][0]["name"]
        if hn == None:
            logger.info("hostname is already null in iDB for host " + hostname)
            return True
        else:
            hn_dict = "inventory-action.pl -q -use_krb_auth -resource host -action update -serialNumber " + serial_number + " -updateFields \"name=null\""
            self.exec_cmd(hn_dict)

            check = json.loads(self.exec_cmd("inventory-action.pl -q -use_krb_auth -resource host -action read -serialNumber " + serial_number + " -fields name"))
            hn = check["data"][0]["name"]
            if hn == None:
                return True
            return False

    def update_files(self, casenum=""):
        in_file = self.user_home + "/" + casenum + "_include"
        ex_file = self.user_home + "/" + casenum + "_exclude"
        cnc_file = self.user_home + "/" + casenum + "_hostinfo"
        in_buf = StringIO()
        ex_buf = StringIO()
        ci = open(cnc_file, "r")
        ci_json = json.load(ci)
        for i in range(len(ci_json)):
            for k, v in ci_json[i].items():
                if(v[0]["cnc_api_url"] == None) or (v[0]["serial_number"] == None):
                    ex_buf.write("{0}".format(k) + ',')
                else:
                    in_buf.write("{0}".format(k) + ',')
        inc = open(in_file, "w")
        logger.debug("include " + in_buf.getvalue().rstrip(','))
        inc.write(in_buf.getvalue().rstrip(','))
        inc.close()
        exc = open(ex_file, "w+")
        logger.debug("exclude " + ex_buf.getvalue())
        exc.write(ex_buf.getvalue())
        exc.close()

    def get_cnc_info(self, hostname):
        """
        This function returns CNC host apiUrl and Serial Number of given hosts from iDB
        :param hostname: hostname
        :return {hostname: [cnc: cnc host, serial: serial number]}
        """

        ci_dict = "inventory-action.pl -q -use_krb_auth -resource hostconfig -action read -host.name " + hostname + " -fields key,value -key apiUrl"
        sn_dict = "inventory-action.pl -q -use_krb_auth -resource host -action read -name " + hostname + " -fields serialNumber"
        rp_dict = "inventory-action.pl -q -use_krb_auth -resource hostconfig -action read -host.name " + hostname + " -fields key,value -key rackUPos"
        cc_dict = "inventory-action.pl -q -use_krb_auth -resource host -action read -host.name " + hostname + " -fields cluster.clusterConfigs.value,cluster.clusterConfigs.type"
        sm_dict = "inventory-action.pl -q -use_krb_auth -resource host -action read -host.name " + hostname + " -fields manufacturer"
             
        try:
            ci_out = json.loads(self.exec_cmd(ci_dict))
            sn_out = json.loads(self.exec_cmd(sn_dict))
            rp_out = json.loads(self.exec_cmd(rp_dict))
            sm_out = json.loads(self.exec_cmd(sm_dict))
            logger.info("Got info for " + hostname)
            cnc_api_url = str(ci_out["data"][0]["value"])
            serial_number = str(sn_out["data"][0]["serialNumber"])
            rack_position = str(rp_out["data"][0]["value"])
            manufacturer = str(sm_out["data"][0]["manufacturer"])

            network_domain = ""
            cc_out = json.loads(self.exec_cmd(cc_dict))
            cluster_configs_list = list(cc_out["data"][0]["cluster"]["clusterConfigs"])
            for i in cluster_configs_list:
                if "network-domain" in i.values():
                    network_domain = i["value"]
                    if network_domain == None or network_domain == "":
                        network_domain = "ops.sfdc.net"
            output = {}
            output.setdefault(str(hostname), []).append({"cnc_api_url": cnc_api_url, "serial_number": serial_number, "rack_position": rack_position, "network_domain": network_domain, "manufacturer": manufacturer, "event": None})

            return output

        except:
            logger.debug("Error: unable to find racktastic apiUrl/serialNumber of " + hostname + " in iDB")
            output = {}
            output.setdefault(str(hostname), []).append({"cnc_api_url": None, "serial_number": None, "rack_position": None, "rack_position": None, "network_domain": None, "manufacturer": None, "event": None})

            return output

    def exec_cmd(self, cmd):
        try:
            logger.debug("executing " + cmd)
            command = Popen([cmd], stdout=PIPE, shell=True)
            (output, err) = command.communicate()
        except CalledProcessError as e:
            logger.error(e)
            sys.exit(1)

        return output

    def trigger_deploy(self, hostname, casenum="", role="", cluster="", superpod="", preserve=False):
        try:
            cnc_inf = open(self.user_home + "/" + casenum + "_hostinfo", "r")
        except IOError:
            logger.error(casenum + "_hostinfo is missing/inaccessible")
        chl = json.load(cnc_inf)
        cnc_api_url = ""
        serial_number = ""
        network_domain = ""
        hl = []
        for i in chl:
            hl.append(i.keys()[0])
        if hostname in hl:
            for i in chl:
                if hostname in i.keys():
                    cnc_api_url = i.values()[0][0]["cnc_api_url"]
                    serial_number = i.values()[0][0]["serial_number"]
                    network_domain = i.values()[0][0]["network_domain"]
                    break
        else:
            raise Exception
        deploy_dict = {}
        try:
            rack_stat_dict = json.loads(self.exec_cmd("curl -s --connect-timeout 10 --request GET " + cnc_api_url + "status"))
            rack_status = rack_stat_dict["rack"]["state"]
        except:
            deploy_dict.setdefault("error", "The rack status could not be fetched in time. Exiting.")
            return deploy_dict
        if not rack_status in ["ready"]:
            deploy_dict.setdefault("error", "The rack status does not match it's expected state: 'ready' <> '" + rack_status + "'. Exiting.")
        else:
            deploy_dict = json.loads(self.exec_cmd("curl -s --request POST " + cnc_api_url + "event -d '{\"type\":\"deploy\",\"serial_number\": \"" + serial_number + "\", \"message\":{\"inventory_idb_cluster_name\":\"" + cluster + "\",\"inventory_idb_superpod_name\":\"" + superpod + "\",\"default_hostname\":\"" + hostname + "." + network_domain + "\",\"host_role\":\"" + role + "\",\"preserve\":\"" + str(preserve).lower() + "\"}}'"))
        return deploy_dict

    def trigger_image(self, hostname, casenum="", role="", preserve=False):
        try:
            cnc_inf = open(self.user_home + "/" + casenum + "_hostinfo", "r")
        except IOError:
            logger.error(casenum + "_hostinfo is missing/inaccessible")
        chl = json.load(cnc_inf)
        cnc_api_url = ""
        serial_number = ""
        hl = []
        for i in chl:
            hl.append(i.keys()[0])
        if hostname in hl:
            for i in chl:
                if hostname in i.keys():
                    cnc_api_url = i.values()[0][0]["cnc_api_url"]
                    serial_number = i.values()[0][0]["serial_number"]
                    break
        else:
            raise Exception
        image_dict = {}
        try:
            rack_stat_dict = json.loads(self.exec_cmd("curl -s --connect-timeout 10 --request GET " + cnc_api_url + "status"))
            rack_status = rack_stat_dict["rack"]["state"]
        except:
            image_dict.setdefault("error", "The rack status could not be fetched in time. Exiting.")
            return image_dict
        if not rack_status in ["ready"]:
            image_dict.setdefault("error", "The rack status does not match it's expected state: 'ready' <> '" + rack_status + "'. Exiting.")
        else:
            image_dict = json.loads(self.exec_cmd("curl -s --request POST " + cnc_api_url + "event -d '{\"type\":\"image\",\"serial_number\":\"" + serial_number + "\",\"message\":{\"name\":\"vanilla\",\"preserve\":\"" + str(preserve).lower() + "\",\"host_role\":\"" + role + "\"}}'"))
        return image_dict
        
    def rebuild_failed(self, hostname, casenum="", preserve=False):
        try:
            cnc_inf = open(self.user_home + "/" + casenum + "_hostinfo", "r")
        except IOError:
            logger.error(casenum + "_hostinfo is missing/inaccessible")
        chl = json.load(cnc_inf)
        cnc_api_url = ""
        serial_number = ""
        hl = []
        for i in chl:
            hl.append(i.keys()[0])
        if hostname in hl:
            for i in chl:
                if hostname in i.keys():
                    cnc_api_url = i.values()[0][0]["cnc_api_url"]
                    serial_number = i.values()[0][0]["serial_number"]
                    break
        else:
            raise Exception
        deploy_dict = {}
        try:
            rack_stat_dict = json.loads(self.exec_cmd("curl -s --connect-timeout 10 --request GET " + cnc_api_url + "status"))
            rack_status = rack_stat_dict["rack"]["state"]
        except:
            deploy_dict.setdefault("error", "The rack status could not be fetched in time. Exiting.")
            return deploy_dict
        if not rack_status in ["ready"]:
            deploy_dict.setdefault("error", "The rack status does not match it's expected state: 'ready' <> '" + rack_status + "'. Exiting.")
        else:
            deploy_dict = json.loads(self.exec_cmd("curl -s --request POST " + cnc_api_url + "event -d '{\"type\":\"rebuild_failed_host\",\"serial_number\": \"" + serial_number + "\",\"message\":{\"name\":\"vanilla\",\"disk_config\":\"stage1v0\",\"preserve\":\"" + str(preserve).lower() + "\"}}'"))
        return deploy_dict

    def fail_host(self, hostname, casenum="",):
        try:
            cnc_inf = open(self.user_home + "/" + casenum + "_hostinfo", "r")
        except IOError:
            logger.error(casenum + "_hostinfo is missing/inaccessible")
        chl = json.load(cnc_inf)
        cnc_api_url = ""
        serial_number = ""
        hl = []
        for i in chl:
            hl.append(i.keys()[0])
        if hostname in hl:
            for i in chl:
                if hostname in i.keys():
                    cnc_api_url = i.values()[0][0]["cnc_api_url"]
                    serial_number = i.values()[0][0]["serial_number"]
                    break
        else:
            raise Exception
        fail_dict = {}
        try:
            rack_stat_dict = json.loads(self.exec_cmd("curl -s --connect-timeout 10 --request GET " + cnc_api_url + "status"))
            rack_status = rack_stat_dict["rack"]["state"]
        except:
            fail_dict.setdefault("error", "The rack status could not be fetched in time. Exiting.")
            return fail_dict
        if not rack_status in ["ready"]:
            fail_dict.setdefault("error", "The rack status does not match it's expected state: 'ready' <> '" + rack_status + "'. Exiting.")
        else:
            fail_dict = json.loads(self.exec_cmd("curl -s --request POST " + cnc_api_url + "event -d '{\"type\":\"fail_host\",\"serial_number\": \"" + serial_number + "\"}'"))
        return fail_dict

    def check_status(self, hostname, casenum=""):
        try:
            cnc_inf = open(self.user_home + "/" + casenum + "_hostinfo", "r")
        except IOError:
            logger.error(casenum + "_hostinfo is missing/inaccessible")

        result = False
        status = None
        seconds = 30
        count = 0
        delay = int(600)
        logger.info("Pausing for " + str(delay) + " seconds while waiting for status change on " + hostname)
        time.sleep(delay)

        chl = json.load(cnc_inf)
        cnc_api_url = ""
        serial_number = ""
        hl = []
        try:
            for i in chl:
                hl.append(i.keys()[0])
            if hostname in hl:
                for i in chl:
                    if hostname in i.keys():
                        cnc_api_url = i.values()[0][0]["cnc_api_url"]
                        serial_number = i.values()[0][0]["serial_number"]
                        break
            else:
                raise Exception
            while result != True:
                if count == 60:
                    logger.info("\nNot able to image/rebuild/deploy %s. Exiting" % hostname)
                    return result, status
                    sys.exit(1)
                status_dict = json.loads(self.exec_cmd("curl -s --request GET " + cnc_api_url + "host/" + serial_number))
                status = status_dict["state"]
                if status in ["awaiting_deployment","deployed"]:
                    result = True
                    break
                logger.info("%s - %s\nRetrying %s in %s seconds" % (hostname, status, hostname, seconds))
                time.sleep(seconds)
                count += 1
            logger.info("\n%s is processed successfully" % hostname)
            return result, status
        except:
            return result, status

    def check_event_status(self, hostname, url=""):
        result = False
        status = None
        delay = 60
        seconds = 30
        count = 0
        logger.info("Pausing %s seconds for event status change on %s" % (str(delay), hostname))
        time.sleep(delay)
        try:
            while result != True:
                if count == 60:
                    logger.error("%s\nEvent state don't match desired statue: 'completed' <> '%s'" % (hostname, status))
                    return result, status
                status_dict = json.loads(self.exec_cmd("curl -s --request GET %s" % url))
                status = status_dict["status"]
                if status in ["completed", "failed"]:
                    result = True
                    break
                logger.info("%s - %s\nRetrying %s in %s seconds" % (hostname, status, url, seconds))
                time.sleep(seconds)
                count += 1
            logger.info("%s event %s" % (hostname, status))
            return result, status
        except:
            return result, status


if __name__ == "__main__":

    parser = ArgumentParser(prog='migration_manager.py', usage="\n %(prog)s \n\t-h --help prints this help \n\t-v verbose output \n\t-c casenum -a cncinfo \n\t-c casenum -a image --role <ROLE> [--preserve] \n\t-c casenum -a delpoy --role <ROLE> --cluster <CLUSTER> --superpod <SUPERPOD> [--preserve] \n\t-c casenum -a rebuild [--preserve] \n\t-c casenum -a status \n\t-c casenum -a erasehostname \n\t-c casenum -a updateopsstatus")

    parser.add_argument("-c", dest="case", help="case number", required=True)
    parser.add_argument("-a", dest="action", help="specify intended action", required=True, choices=["cncinfo", "image", "deploy", "rebuild", "failhost", "status", "erasehostname", "updateopsstatus"])
    parser.add_argument("--role", dest="host_role", help="specify host role")
    parser.add_argument("--cluster", dest="cluster_name", help="specify cluster name")
    parser.add_argument("--superpod", dest="superpod_name", help="specify super pod name")
    parser.add_argument("--preserve", dest="preserve_data", action="store_true", help="include this to preserve data", default=False)
    parser.add_argument("-v", dest="verbose", action="store_true", help="verbose output", default=False)

    args = parser.parse_args()

    user_home = path.expanduser('~')

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger()
    
    mig = Migration()
    
    if not mig.has_valid_kerb_ticket():
        logger.error("please kinit to continue")
        sys.exit(1)
    if args.case:
        try:
            hostlist = open(str(user_home + "/" + args.case + "_include"), "r")
        except:
            logger.error(args.case+"_include file is missing")
            sys.exit(1)
        if args.action:
            action_swither = {
                "cncinfo": mig.get_cnc_info,
                "image": mig.trigger_image,
                "deploy": mig.trigger_deploy,
                "rebuild": mig.rebuild_failed,
                "failhost": mig.fail_host,
                "status": mig.check_status,
                "erasehostname": mig.erase_hostname,
                "updateopsstatus": mig.update_ops_status
            }
            f = action_swither.get(args.action)
            hl = []
            hlist = hostlist.readline()
            if hlist == "":
                logger.error("hostlist empty")
                sys.exit(1)
            hl = hlist.rstrip('\n').rstrip(',').split(",")
            pool = Pool(10)
            if args.action == "cncinfo":
                info = pool.map(f, hl)
            elif args.action == "erasehostname" or args.action == "updateopsstatus":
                temp = partial(f, casenum=args.case)
                info = pool.map(temp, hl)
            elif args.action == "image":
                temp = partial(f, casenum=args.case, role=args.host_role.upper(), preserve=args.preserve_data)
                info = pool.map(temp, hl)
            elif args.action == "deploy":
                temp = partial(f, casenum=args.case, role=args.host_role, cluster=args.cluster_name.upper(), superpod=args.superpod_name.upper(), preserve=args.preserve_data)
                info = pool.map(temp, hl)
            elif args.action == "rebuild":
                temp = partial(f, casenum=args.case, preserve=args.preserve_data)
                info = pool.map(temp, hl)
            elif args.action == "failhost":
                temp = partial(f, casenum=args.case)
                info = pool.map(temp, hl)
            elif args.action == "status":
                hosts_completed = {}
                queue = Queue.Queue()
                for i in range(10):
                    t = ThreadHosts(queue, args.case, hosts_completed)
                    t.setDaemon(True)
                    t.start()

                for h in hl:
                    lst = [h, args.case, int(60)]
                    queue.put(lst)

                queue.join()
                logger.debug(hosts_completed)

                for key in hosts_completed:
                    if not hosts_completed[key] in ["awaiting_deployment", "deployed"]:
                        logger.error("Error processing one of the hosts")
                        logger.info(hosts_completed)
                        sys.exit(1)
                logger.info(hosts_completed)

            pool.close()
            pool.join()

            if args.action == "cncinfo":
                cnc_info = open(str(user_home + "/" + args.case + "_hostinfo"), "w+")
                json.dump(info, cnc_info)  # cnc_info.write(str(info))
                cnc_info.close()
                cnc_list = []
                for o in info:
                    if not o.values()[0][0]["cnc_api_url"] == None:
                        if o.values()[0][0]["manufacturer"] in ["HP", "HPE"]:
                            cnc_list.append(o.values()[0][0]["cnc_api_url"].split("//")[1].split(".")[0])
                cnc = open(str(user_home + "/" + args.case + "_cnc"), "w+")
                if not (len(cnc_list) > 0 and info[0].values()[0][0]["cnc_api_url"] == None):
                    cnc_list.append(info[0].values()[0][0]["cnc_api_url"].split("//")[1].split(".")[0])
                cnc.write(','.join(cnc_list))
                cnc.close()
                mig.update_files(casenum=args.case)
                sys.exit(0)
            elif args.action in ["image", "rebuild", "deploy", "failhost"]:
                stat = []

                # writing returned event ids to against respective host in hostinfo file
                update_hostinfo = open(user_home + "/" + args.case + "_hostinfo", "r")
                hinfo = json.load(update_hostinfo)
                update_hostinfo.close()
                for i in range(len(info)):
                    if "status" in info[i].keys():
                        logger.info(hl[i] + " - [" + str(info[i]["id"]) + "] " + str(info[i]["type"]) + " - " + str(info[i]["status"]))
                        if hl[i] in hinfo[i].keys():
                            logger.info("updating event id as %s for %s" % (hl[i], info[i]["id"]))
                            hinfo[i].values()[0][0]["event"] = info[i]["id"]
                    elif "error" in info[i].keys():
                        logger.info(hl[i] + " - " + info[i]["error"])
                        stat.append(hl[i])
                update_hostinfo = open(user_home + "/" + args.case + "_hostinfo", "w")
                json.dump(hinfo, update_hostinfo)
                update_hostinfo.close()

                # checking for the image/rebuild/deploy/failhost event status completed or not
                processed_hosts = {}
                queue = Queue.Queue()
                logger.debug(hl)
                for i in range(len(hl)):
                    t = ImageStatusThreads(queue, processed_hosts)
                    t.setDaemon(True)
                    t.start()
                for i in range(len(hl)):
                    if hl[i] in hinfo[i].keys():
                        event = hinfo[i].values()[0][0]["event"]
                        cnc_api_url = hinfo[i].values()[0][0]["cnc_api_url"]
                        event_url = str(cnc_api_url) + "event/" + str(event)
                        if not event == None:
                            lst = [hl[i], event_url, int(60)]
                            queue.put(lst)
                queue.join()

                for key in processed_hosts:
                    if processed_hosts[key] == "failed":
                        logger.error("Error processing event on %s" % key)
                        stat.append(key)
                    elif not processed_hosts[key] == "completed":
                        logger.info("%s unable to process with in time. Please check event status manually." % key)
                logger.info(processed_hosts)
 
                if len(stat) > 0:
                    logger.error(args.action + " event failed on follwoing hosts. please retry: \n" + ','.join(list(set(stat))))
                    # logger.error("moving follwoing hosts to exclude file from include file: \n" + ','.join(list(set(stat))))
                    # inf = open(user_home + "/" + args.case + "_include", "r")
                    # exf = open(user_home + "/" + args.case + "_exclude", "r")
                    # inh = inf.readline().rstrip("\n").rstrip(",").split(",")
                    # exh = exf.readline()
                    # final_inh = []
                    # final_exh = []
                    # for h in stat:
                    #     logger.debug("removing %s" % h)
                    #     idx = inh.index(h)
                    #     final_exh.append(inh.pop(idx))
                    #     final_inh = inh
                    # logger.info("include: " + ','.join(final_inh).rstrip(','))
                    # logger.info("exclude: " + ','.join(final_exh).rstrip(','))
                    # inf = open(user_home + "/" + args.case + "_include", "w")
                    # exf = open(user_home + "/" + args.case + "_exclude", "w")
                    # inf.write(','.join(final_inh).rstrip(','))
                    # exf.write(','.join(final_exh) + exh)
                    # sys.exit(1)
                sys.exit(0)
            elif args.action == "erasehostname":
                failed_hosts = []
                for i in range(len(info)):
                    if not info[i]:
                        failed_hosts.append(hl[i])
                    else:
                        logger.info(hl[i] + " - SUCCESS")
                if len(failed_hosts) > 0:
                    for h in failed_hosts:
                        logger.error("unable to erase hostname in iDB for host " + h)
                    sys.exit(1)
                else:
                    sys.exit(0)
            elif args.action == "updateopsstatus":
                failed_hosts = []
                for i in range(len(info)):
                    if info[i]:
                        logger.info(hl[i] + " - SUCCESS")
                    else:
                        failed_hosts.append(hl[i])
                if len(failed_hosts) > 0:
                    for h in failed_hosts:
                        logger.error("unable to update host operational status to ACTIVE in iDB for host " + h)
                    sys.exit(1)
                else:
                    sys.exit(0)
        else:
            logger.error("action must be specified. check help for more information")
            sys.exit(1)

    else:
        logger.error("case number is not provided. use -c CASENUM")
        sys.exit(1)
