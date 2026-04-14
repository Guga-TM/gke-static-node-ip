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

import os, time, json, yaml, signal, sys, requests
from kubernetes import client,config, utils,watch
from logger import log_info, log_error, log_system
from collections import defaultdict

component = "distributor"

def handle_sigterm(signum, frame):
    log_info(component, "received SIGTERM, deleting controller daemonset...")
    delete_ds_resource()
    log_system(f"received SIGTERM, exiting {component}...")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

def wait_for_fixer_ready(timeout=300):
    log_info(component, f"checking if fixer pod is ready")
    namespace = os.environ['NAMESPACE']
    v1 = client.CoreV1Api()
    w = watch.Watch()

    for event in w.stream(v1.list_namespaced_pod, namespace=namespace, 
                          label_selector=f"component=fixer", 
                          timeout_seconds=timeout):
        pod = event['object']
        
        # Check if pod has status conditions
        if pod.status.conditions:
            for condition in pod.status.conditions:
                # The 'Ready' condition must be 'True'
                if condition.type == 'Ready' and condition.status == 'True':
                    log_info(component, f"pod {pod.metadata.name} is ready")
                    w.stop()
                    return True
    log_error(component, "timed out waiting for fixer to be ready")
    raise TimeoutError

def get_k8s_nodes_from_nodepool(nodepool):
    v1 = client.CoreV1Api()
    
    label_selector = f"cloud.google.com/gke-nodepool={nodepool}"

    # List nodes matching the label selector
    nodes = v1.list_node(label_selector=label_selector)

    schedulable_nodes = [
        node.metadata.name for node in nodes.items 
        if not node.spec.unschedulable
    ]
    
    return schedulable_nodes

def get_zone_of_k8s_node(node):
    zone_label = 'topology.gke.io/zone'
    v1 = client.CoreV1Api()
    
    node_name = node

    # encountered an issue when the node exists but this label is unavailable
    # so implemented this retry loop
    attempts_count = 15

    for i in range(1, attempts_count+1):
        node_info = v1.read_node(name=node_name)
        labels = node_info.metadata.labels
        zone = labels.get(zone_label)
        if zone is not None and zone != '':
            return zone
        time.sleep(1)
    
    log_error(component, f"failed getting GCP zone for the node {node}")
    log_error(component, "this issue is not recoverable, exiting now...")
    raise KeyError

def get_current_ip_of_node(node):
    url = 'http://fixer:6924/get_ip_of_node'
    zone = get_zone_of_k8s_node(node)
    data = {'instance_name': node, 'zone': zone}

    log_info(component, f"sending request to get current IP of {node}")

    # sending post request
    try:
        response = requests.post(url, json=data, timeout=180)
    except requests.exceptions.HTTPError as http_err:
        log_error(component, f"request to fixer API failed with HTTP exception {http_err}")  # e.g., 404 Not Found
        return "-1"
    except requests.exceptions.ConnectionError as conn_err:
        log_error(component, f"request to fixer API failed with connection exception {conn_err}")  # DNS or network issue
        return "-1"
    except requests.exceptions.Timeout as timeout_err:
        log_error(component, f"request to fixer API failed with timeout exception {timeout_err}")  # Server took too long
        return "-1"
    except requests.exceptions.RequestException as req_err:
        log_error(component, f"request to fixer API failed with exception {req_err}")
        return "-1"

    status = response.status_code
    resp_data = response.text
    if status == 200 :
        log_info(component, "got response 200 from fixer")
        return resp_data
    else:
        log_error(component, f"request to fixer API failed with {status} error")
        log_error(component, "check fixer error logs")
        return "-1"

def has_correct_ip(node, desired_ips):
    current_ip = get_current_ip_of_node(node)
    if current_ip == "-1":
        log_error(component, "failed to check if current IP is one of desired IPs")
        log_error(component, "will assume that IP is incorrect")
        return False, current_ip
    else:
        log_info(component, f"got information that IP of node {node} is now {current_ip}")
        return current_ip in desired_ips, current_ip

def assign_ips_to_nodes(nodes_data_old, nodes_now, desired_ips):
    this_nodepool_assignment_config = defaultdict(dict)
    
    for node in nodes_now:
        if node in nodes_data_old: # no redistribution required
            # add this node config as is
            this_nodepool_assignment_config[node]=nodes_data_old[node]
            # and remove IP from set of desired IPs
            desired_ips.remove(nodes_data_old[node]['desired_ip'])
        elif (curr_ip := has_correct_ip(node, desired_ips))[0]:
            this_nodepool_assignment_config[node]['desired_ip'] = curr_ip[1]
            this_nodepool_assignment_config[node]['gcp_zone'] = get_zone_of_k8s_node(node)

    # it's two loops because we first need to remove all used IPs from desired
    for node in nodes_now:
        if node not in nodes_data_old: # redistribution required
            this_nodepool_assignment_config[node]['desired_ip'] = desired_ips.pop(0)
            this_nodepool_assignment_config[node]['gcp_zone'] = get_zone_of_k8s_node(node)

    return this_nodepool_assignment_config

def distribute_across_nodepool(nodepool, desired_ips, nodes_data_old):
    nodes_data_parsed = {}
    nodes = get_k8s_nodes_from_nodepool(nodepool) # get schedulable nodes in current nodepool
    if len(nodes) == len(desired_ips):
        nodes_data_parsed |= assign_ips_to_nodes(nodes_data_old, nodes, desired_ips)
    elif len(nodes) > len(desired_ips):
        log_error(component, f"found {len(nodes)} nodes, but have only {len(desired_ips)} IPs to assign")
        log_error(component, "this may be ok if there are node upgrades now")
    else:
        log_error(component, f"misconfiguration - found {len(nodes)} nodes and {len(desired_ips)} IPs to assign")
        log_error(component, "check your values.yaml file. Number of nodes in the nodepool and number of IPs to assign must be equal")
    
    return nodes_data_parsed

def process_raw_nodes_data(nodes_data_loaded, nodes_data_raw):
    nodes_data_parsed = {} # resulting dictionary

    for nodepool in nodes_data_raw:
        desired_ips = nodes_data_raw[nodepool]
        nodes_data_parsed |= distribute_across_nodepool(nodepool, desired_ips, nodes_data_loaded)
            
    log_info(component, "processed data:")
    log_info(component, nodes_data_parsed)

    return nodes_data_parsed

def monitor_nodes_data(nodes_data_parsed, nodes_data_raw):
    nodes_loaded_into_memory = set()
    for node in nodes_data_parsed:
        nodes_loaded_into_memory.add(node)
    log_info(component, "got this data loaded into memory now:")
    log_info(component, nodes_data_parsed)

    nodes_now = set()
    for nodepool in nodes_data_raw:
        nodes_now |= set(get_k8s_nodes_from_nodepool(nodepool))
    log_info(component, "actual list of nodes from nodepools that need to be managed:")
    log_info(component, nodes_now)
    
    if nodes_loaded_into_memory == nodes_now:
        log_info(component, "everything is ok, no need to redistribute IPs")
    else:
        log_system("requesting redistribution of IP addresses: new nodes detected")
        nodes_data_parsed = process_raw_nodes_data(nodes_data_parsed, nodes_data_raw)
    
    return nodes_data_parsed

def update_ds_resource(nodes_data_parsed):
    apps_v1 = client.AppsV1Api()

    nodes_data_jsonstr = json.dumps(nodes_data_parsed)
    namespace = os.environ['NAMESPACE']
    new_env_var = {"name": "NODES_DATA", "value": nodes_data_jsonstr}

    patch_body = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": 'controller',
                            "env": [new_env_var] # Merges/adds to existing env list
                        }
                    ]
                }
            }
        }
    }

    try:
        api_response = apps_v1.patch_namespaced_daemon_set(
            name='controller',
            namespace=namespace,
            body=patch_body
        )
        log_info(component, "updated controller daemonset")
        return api_response
    except client.exceptions.ApiException as e:
        log_error(component, "exception when patching ConfigMap controller-config")

def create_ds_resource_from_yaml():
    k8s_api = client.ApiClient()
    namespace = os.environ['NAMESPACE']

    # Create the resource
    try:
        utils.create_from_yaml(k8s_api, 'controller.yaml', namespace=namespace, apply=True)
        log_info(component, "created controller daemonset")
    except utils.FailToCreateError as e:
        log_error(component, "failed creating controller daemonset")
        for api_exception in e.api_exceptions:
            if api_exception.status == 409:
                log_error(component, "already exists")

def delete_ds_resource():
    k8s_api = client.AppsV1Api()
    namespace = os.environ['NAMESPACE']

    log_info(component, 'deleting controller daemonset')

    try:
        api_response = k8s_api.delete_namespaced_daemon_set(
            name='controller',
            namespace=namespace,
            propagation_policy='Background'
        )
        log_info(component, "deleted controller daemonset")
    except client.exceptions.ApiException as e:
        log_error(component, "failed deleting controller daemonset")

def distributor():
    log_system("############## INITIALIZING GKE-STATIC-NODE-IP-DISTRIBUTOR ##############")
    config.load_incluster_config()
    # we need fixer to be ready before starting distributor
    wait_for_fixer_ready()
    # get data for all nodes from json
    json_data_env = os.environ['NODES_DATA_RAW']
    log_info(component, "loaded data from env:")
    log_info(component, json_data_env)
    nodes_data_raw = json.loads(json_data_env)
    log_info(component, "loaded json data")
    nodes_data_parsed = process_raw_nodes_data(
        nodes_data_loaded={},
        nodes_data_raw=nodes_data_raw
    )
    log_info(component, "processed data:")
    log_info(component, nodes_data_parsed)
    create_ds_resource_from_yaml()
    update_ds_resource(nodes_data_parsed)
    check_rate = int(os.getenv('CHECK_RATE_SECONDS', '60'))
    log_info(component, f"check_rate: {check_rate}")
    try:
        log_system("############## STARTING GKE-STATIC-NODE-IP-DISTRIBUTOR ##################")
        while True:
            nodes_data_parsed = monitor_nodes_data(nodes_data_parsed, nodes_data_raw)
            time.sleep(check_rate)
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        log_info(component, "control loop stopped")

if __name__ == "__main__":
    distributor()