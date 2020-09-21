from os import path
import re
import json
import requests
import time
requests.packages.urllib3.disable_warnings()


class Gingham:
    instance = "https://gingham1-0-crz.data.sfdc.net"
    user_home = path.expanduser("~/.cptops/auth")

    def __init__(self):
        self.instance_url = Gingham.instance + "/api"
        self.headers = {"Gingham-version": "2.0",
                        "Content-type": "application/json"}
        self.cacert = Gingham.user_home + "/root_intermediate_cert.pem"
        self.cert = Gingham.user_home + "/gingham_cert_chain.pem"
        self.key = Gingham.user_home + "/gingham_key.pem"
        self.success_response = ""
        self.error_response = ""

    def get_estate_id_from_host(self, host):
        """
        Method that takes in host fqdn and return it's estate id
        """

        url = self.instance_url + "/operations/estatefromhost/" + host
        try:
            req = requests.get(url, cert=(self.cert, self.key),
                               verify=self.cacert, headers=self.headers)
            response = req.json()
            if req.status_code == 200:
                if response['type'] == "ok":
                    return response['message']
            else:
                raise Exception
        except Exception as e:
            print("{}: {}".format(req.status_code, response["message"]))

    def get_estate_status(self, estate_id):
        """
        Method that takes in estate id and return it's status
        """
        self.success_response = {}
        url = self.instance_url + "/estates/status/" + estate_id
        try:
            req = requests.get(url, cert=(self.cert, self.key),
                               verify=self.cacert, headers=self.headers)
            if req.status_code == 200:
                response = req.json()
                if response['type'] == "ok":
                    self.success_response.update(
                        {"type": response['type'], "status": response['message']['estate']['status']})
                    return True
                else:
                    raise Exception
            else:
                raise Exception
        except Exception as e:
            self.error_response = "{} - Error processing request in Gingham\n{}".format(
                req.status_code, e)
            return False

    def get_host_status(self, estate_id, host):
        """
        Method that takes in estate, host and returns a host status
        """
        self.success_response = {}
        nohosts = False
        found = False
        url = self.instance_url + "/estates/status/" + estate_id
        try:
            req = requests.get(url, cert=(self.cert, self.key),
                               verify=self.cacert, headers=self.headers)
            if req.status_code == 200:
                response = req.json()
                if response['type'] == "ok":
                    host_placement_location = response['message']['estate']['hostPlacementLocation']
                    for k in host_placement_location.keys():
                        if "hosts" in host_placement_location[k].keys():
                            for host_obj in host_placement_location[k]["hosts"]:
                                if host == host_obj["name"]:
                                    self.success_response.update(
                                        {"status": host_obj["status"], "message": host_obj["hostStatusMessage"]})
                                    found = True
                                    break
                                else:
                                    found = False
                        else:
                            nohosts = True
                    if nohosts:
                        self.error_response = "No valid hosts found in this estate {}".format(estate_id)
                        return False
                    if not found:
                        self.error_response = "Host {} not found in this estate {}".format(host, estate_id)
                        return False
                    return True
                else:
                    raise Exception
            else:
                raise Exception
        except Exception as e:
            self.error_response = "{} - Error processing request in Gingham\n{}".format(
                req.status_code, e)
            return False

    def trigger_reboot_on_hosts(self, hosts, estate_id, change_case_id):
        """
        Method that triggers reboot action on a given list of hosts.
        All hosts in the list must belong to the same estate_id
        """
        url = self.instance_url + "/host/reboot"
        kingdom = estate_id.split(".")[0]
        # hosts = list().append(host)
        payload = {"kingdom": kingdom, "estate": estate_id,
                   "hosts": hosts, "changeCaseId": change_case_id}

        try:
            req = requests.post(url, data=json.dumps(payload), cert=(
                self.cert, self.key), verify=self.cacert, headers=self.headers)
            if req.status_code >= 200 and req.status_code < 300:
                response = req.json()
                if response['type'] == "reboot":
                    self.success_response = response['message']
                    return True
            else:
                raise Exception
        except Exception as e:
            self.error_response = "{}: Error processing request in Gingham\n{}".format(
                req.status_code, e)
            return False

    def reimage_hosts(self, hosts, estate_id, change_case_id, preserve=False):
        """
        Method that triggers reimage action on a given list of hosts.
        All hosts in the list must belong to the same estate_id
        """
        url = self.instance_url + "/host/reimage"
        kingdom = estate_id.split(".")[0]
        # hosts = list().append(host)
        payload = {"kingdom": kingdom, "estate": estate_id, "hosts": hosts,
                   "changeCaseId": change_case_id, "preserveData": preserve}
        result = {}
        try:
            req = requests.post(url, data=json.dumps(payload), cert=(
                self.cert, self.key), verify=self.cacert, headers=self.headers)
            response = req.json()
            if response['type'] == "reimage":
                result.update({"status_code": req.status_code, "message": response["message"]})
                return True, result
            else:
                result.update({"status_code": req.status_code, "error": response["message"]})
                return False, result
        except Exception as e:
            self.error_response = "Error processing request in Gingham\n{}".format(e)
            result.update({"status_code": 999, "error": self.error_response})
            return False, result

    def monitor_workorder_progress(self, hosts, estate_id, wo_type="reimage"):
        """
        Method that checks the reboot work order status for given estate and host
        """
        url = self.instance_url + \
            "/workorders/HOSTOP/{}_{}".format(estate_id, wo_type)
        expected_task_status = "COMPLETED"
        expected_op_statuses = ["ACTIVE", "COMPLETED"]
        workorder_dict = {}
        try:
            req = requests.get(url, cert=(self.cert, self.key),
                               verify=self.cacert, headers=self.headers)
            if req.status_code == 200:
                response = req.json()
                end_time = ""
                if response['type'] == "ok":
                    start_time = response['message']['start']
                    if response['message']['status'] == 'COMPLETED':
                        end_time = response['message']['end']
                    for h in hosts:
                        h_stat = self.get_host_status(estate_id, h)
                        if h_stat:
                            workorder_dict.update({h: self.success_response})
                        else:
                            workorder_dict.update({h: {"error": self.error_response}})
                    workorder_dict["start_time"] = start_time
                    workorder_dict["end_time"] = end_time
                    workorder_dict["status"] = response['message']['status']
                self.success_response = workorder_dict
                return True
            else:
                raise Exception
        except Exception as e:
            self.error_response = "{}: Error processing request in Gingham\n{}".format(
                req.status_code, e)
            return False
