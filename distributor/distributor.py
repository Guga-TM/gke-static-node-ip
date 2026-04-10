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

import os, time, json
from kubernetes import client,config
from logger import log_info, log_error, log_system
from collections import defaultdict

component = "distributor"

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
    attempts_count = 5

    for i in range(1, attempts_count+1):
        node_info = v1.read_node(name=node_name)
        labels = node_info.metadata.labels
        zone = labels.get(zone_label)
        if zone is not None and zone != '':
            return zone
    
    log_error(component, f"failed getting GCP zone for the node {node}")
    log_error(component, "this issue is not recoverable, exiting now...")
    raise KeyError

def assign_ips_to_nodes(nodes, ips):
    this_nodepool_assignment_config = defaultdict(dict)
    for node in nodes:
        this_nodepool_assignment_config[node]['desired_ip'] = ips.pop(0)
        this_nodepool_assignment_config[node]['gcp_zone'] = get_zone_of_k8s_node(node)
    return this_nodepool_assignment_config

def get_process_raw_nodes_data_from_json():
    # get data for all nodes from json
    json_data_env = os.environ['NODES_DATA_RAW']
    log_info(component, "loaded data from env:")
    log_info(component, json_data_env)
    nodes_data_raw = json.loads(json_data_env)

    nodes_data_parsed = {} # resulting dictionary

    for nodepool in nodes_data_raw:
        desired_ips = nodes_data_raw[nodepool] # get data from JSON
        nodes = get_k8s_nodes_from_nodepool(nodepool) # get schedulable nodes in current nodepool
        if len(nodes) == len(desired_ips):
            nodes_data_parsed |= assign_ips_to_nodes(nodes, desired_ips)
        elif len(nodes) > len(desired_ips):
            log_error(component, f"found {len(nodes)} nodes, but have only {len(desired_ips)} IPs to assign")
            log_error(component, "this may be ok if there are node upgrades now")
        else:
            log_error(component, f"misconfiguration - found {len(nodes)} nodes and {len(desired_ips)} IPs to assign")
            log_error(component, "check your values.yaml file. Number of nodes in the nodepool and number of IPs to assign must be equal")
            
    log_info(component, "processed data:")
    log_info(component, nodes_data_parsed)

    return nodes_data_parsed

def monitor_nodes_data(nodes_data_parsed):
    nodes_loaded_into_memory = set()
    for node in nodes_data_parsed:
        nodes_loaded_into_memory.add(node)
    log_info(component, "got this data loaded into memory now:")
    log_info(component, nodes_data_parsed)

    json_data_env = os.environ['NODES_DATA_RAW']
    nodes_data_raw = json.loads(json_data_env)
    nodes_now = set()
    for nodepool in nodes_data_raw:
        nodes_now |= set(get_k8s_nodes_from_nodepool(nodepool))
    log_info(component, "actual list of nodes from nodepools that need to be managed:")
    log_info(component, nodes_now)
    
    if nodes_loaded_into_memory == nodes_now:
        log_info(component, "everything is ok, no need to redistribute IPs")
    else:
        log_system("requesting redistribution of IP addresses: new nodes detected")
        nodes_data_parsed = update_nodes_data(nodes_data_parsed, nodes_now, nodes_data_raw)
    
    return nodes_data_parsed

def redistribute_ips_in_nodepool(nodes_data_old, nodes_now, desired_ips):
    this_nodepool_assignment_config = defaultdict(dict)
    
    for node in nodes_now:
        if node in nodes_data_old: # no redistribution required
            # add this node config as is
            this_nodepool_assignment_config[node]=nodes_data_old[node]
            # and remove IP from set of desired IPs
            desired_ips.remove(nodes_data_old[node]['desired_ip'])

    # it's two loops because we first need to remove all used IPs from desired
    for node in nodes_now:
        if node not in nodes_data_old: # redistribution required
            this_nodepool_assignment_config[node]['desired_ip'] = desired_ips.pop(0)
            this_nodepool_assignment_config[node]['gcp_zone'] = get_zone_of_k8s_node(node)

    return this_nodepool_assignment_config

def update_nodes_data(nodes_data_loaded, nodes_data_raw):
    nodes_updated = {}

    for nodepool in nodes_data_raw:
        desired_ips = nodes_data_raw[nodepool] # get data from JSON
        nodes = get_k8s_nodes_from_nodepool(nodepool) # get schedulable nodes in current nodepool
        if len(nodes) == len(desired_ips):
            nodes_updated |= redistribute_ips_in_nodepool(nodes_data_loaded, nodes, desired_ips)
        elif len(nodes) > len(desired_ips):
            log_error(component, f"found {len(nodes)} nodes, but have only {len(desired_ips)} IPs to assign")
            log_error(component, "this may be ok if there are node upgrades now")
        else:
            log_error(component, f"misconfiguration - found {len(nodes)} nodes and {len(desired_ips)} IPs to assign")
            log_error(component, "check your values.yaml file. Number of nodes in the nodepool and number of IPs to assign must be equal")
    
    log_info(component, "updated nodes data:")
    log_info(component, nodes_updated)
    return nodes_updated

def update_ds_resource(nodes_data_parsed):
    apps_v1 = client.AppsV1Api()

    nodes_data_jsonstr = json.dumps(nodes_data_parsed)

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
            namespace='gke-static-node-ip', # todo fix this
            body=patch_body
        )
        log_info(component, "updated controller daemonset")
        return api_response
    except client.exceptions.ApiException as e:
        log_error(component, "exception when patching ConfigMap controller-config")

def distributor():
    log_system("############## INITIALIZING GKE-STATIC-NODE-IP-DISTRIBUTOR ##############")
    config.load_incluster_config()
    nodes_data_parsed = get_process_raw_nodes_data_from_json()
    check_rate = int(os.getenv('CHECK_RATE_SECONDS', '60'))
    log_info(component, f"check_rate: {check_rate}")
    try:
        log_system("############## STARTING GKE-STATIC-NODE-IP-DISTRIBUTOR ##################")
        while True:
            update_ds_resource(nodes_data_parsed)
            nodes_data_parsed = monitor_nodes_data(nodes_data_parsed)
            time.sleep(check_rate)
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        log_info(component, "control loop stopped")

if __name__ == "__main__":
    distributor()