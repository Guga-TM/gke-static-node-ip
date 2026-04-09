# GKE static Node IP controller
# Copyright (C) 2026  Guga Mikulich

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# email for contacts: aragornguga@gmail.com

import os, time, requests, ipaddress, json
from logger import log_info, log_error, log_system

component = "controller"

def validate_ipv4(ip_str):
    try:
        ipaddress.IPv4Address(ip_str)
        return True
    except ValueError:
        log_error(component, f"Wrong IP address format, got {ip_str}")
        ipaddress.IPv4Address(ip_str)
        return False

def get_current_ip():
    url = 'https://api.ipify.org?format=json'
    current_ip = ''
    attempts_count = 10
    single_attempt_timeout = 5
    log_info(component, "sending request to api.ipify.org to check current IP")

    for i in range(1, attempts_count+1):
        try:
            response = requests.get(url, timeout=single_attempt_timeout)
            # convert response to json
            ipinfo_data = response.json()
            current_ip = ipinfo_data['ip']
        except requests.exceptions.Timeout:
            if i < attempts_count:
                log_info(component, f"the request timed out, trying again - attempt {i}")
            else:
                log_error(component, f"the request timed out {attempts_count} times")
                log_error(component, "assuming that internet is not reachable on this node")
                return "-1"

    # use IP validator function to check current ip string
    log_info(component, "sending request to check current IP format validity")
    validate_ipv4(current_ip)

    return current_ip

def get_node_data_from_json(current_node):
    # get data for all nodes from json
    json_data_env = os.environ['NODES_DATA']
    nodes_data = json.loads(json_data_env)

    # get data for current node
    try:
        current_node_data = nodes_data[current_node]
    except KeyError as key_err:
        log_error(component, f"Couldn't find data for {current_node}")
        raise KeyError(key_err)

    desired_ip = current_node_data['desired_ip']
    gcp_zone = current_node_data['gcp_zone']

    # todo move this validation to operator
    log_info(component, "checking desired IP format validity...")
    validate_ipv4(desired_ip)

    return gcp_zone, desired_ip

def send_fix_request(instance_name, instance_zone, desired_ip):
    url = 'http://fixer:6924/fix'
    data = {'instance_name': instance_name, 'zone': instance_zone, 'desired_ip': desired_ip}

    # sending post request
    response = requests.post(url, json=data, timeout=180)

    status = response.status_code
    resp_data = response.text
    if status == 200 :
        log_info(component, "got response 200 from fixer")
    else:
        log_error(component, f"request to fixer API failed with {status} error")
        log_error(component, "check fixer error logs")

def controller():
    log_system("############## INITIALIZING GKE-STATIC-NODE-IP-CONTROLLER ##############")
    instance_name = os.environ['NODE_NAME']
    instance_zone, desired_ip = get_node_data_from_json(instance_name)
    check_rate = int(os.getenv('CHECK_RATE_SECONDS', '15'))
    log_info(component, f"got these values for env vars:")
    log_info(component, f"instance_name: {instance_name}")
    log_info(component, f"instance_zone: {instance_zone}")
    log_info(component, f"desired_ip: {desired_ip}")
    log_info(component, f"check_rate: {check_rate}")
    try:
        log_system("############## STARTING GKE-STATIC-NODE-IP-CONTROLLER ##################")
        while True:
            current_ip = get_current_ip()
            if current_ip == '-1':
                log_error(component, "sending last-resort request to fixer")
                send_fix_request(instance_name, instance_zone, desired_ip)
                log_system("end of fix loop on controller's side")
            elif not current_ip == desired_ip:
                log_error(component, f"found problem: current IP is {current_ip}, but desired is {desired_ip}")
                log_info(component, "sending request to fixer")
                send_fix_request(instance_name, instance_zone, desired_ip)
                log_system("end of fix loop on controller's side")
            else:
                log_info(component, "current IP matches desired IP")
            time.sleep(check_rate)
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        log_info(component, "control loop stopped")

if __name__ == "__main__":
    controller()