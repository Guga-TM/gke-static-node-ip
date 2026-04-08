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
    node_info = v1.read_node(name=node_name)

    labels = node_info.metadata.labels
    zone = labels.get(zone_label)
    return zone

def assign_ips_to_nodes(nodes, ips):
    this_nodepool_assignment_config = defaultdict(dict)
    for node in nodes:
        this_nodepool_assignment_config[node]['desired_ip'] = ips.pop()
        this_nodepool_assignment_config[node]['gcp_zone'] = get_zone_of_k8s_node(node)
    return this_nodepool_assignment_config

def get_process_raw_nodes_data_from_json():
    # get data for all nodes from json
    json_data_env = os.environ['NODES_DATA_RAW']
    nodes_data_raw = json.loads(json_data_env)

    nodes_data_parsed = {} # resulting dictionary

    for nodepool in nodes_data_raw:
        desired_ips = nodes_data_raw[nodepool] # get data from JSON
        desired_ips_set = set(desired_ips) # convert to Set
        nodes = get_k8s_nodes_from_nodepool(nodepool) # get schedulable nodes in current nodepool
        if len(nodes) == len(desired_ips_set):
            nodes_data_parsed |= assign_ips_to_nodes(nodes, desired_ips_set)
        elif len(nodes) > len(desired_ips_set):
            log_error(component, f"found {len(nodes)} nodes, but have only {len(desired_ips_set)} IPs to assign")
            log_error(component, "this may be ok if there are node upgrades now")
        else:
            log_error(component, f"misconfiguration - found {len(nodes)} nodes and {len(desired_ips_set)} IPs to assign")
            log_error(component, "check your values.yaml file. Number of nodes in the nodepool and number of IPs to assign must be equal")
            
    
    return nodes_data_parsed

def monitor_update_nodes_data(nodes_data_parsed):
    nodes_loaded_into_memory = {}
    for node in nodes_data_parsed:
        nodes_loaded_into_memory.add(node)
    log_info(component, "got this nodes loaded into memory now:")
    log_info(component, nodes_loaded_into_memory)

    json_data_env = os.environ['NODES_DATA_RAW']
    nodes_data_raw = json.loads(json_data_env)
    nodes_now = {}
    for nodepool in nodes_data_raw:
        nodes_now |= set(get_k8s_nodes_from_nodepool(nodepool))
    log_info(component, "actual list of nodes from nodepools that need to be managed:")
    log_info(component, nodes_now)

    if nodes_loaded_into_memory == nodes_now:
        log_info(component, "everything is ok, no need to redistribute IPs")
    else:
        log_system("requesting redistribution of IP addresses: new nodes detected")
        nodes_data_parsed = get_process_raw_nodes_data_from_json()
    
    return nodes_data_parsed

def update_cm_resource(nodes_data_parsed):
    v1 = client.CoreV1Api()

    nodes_data_jsonstr = json.dumps(nodes_data_parsed)

    patch_body = {
        'data': {
            'dynamic_json_nodes_data': nodes_data_jsonstr
        }
    }

    try:
        # Perform the patch
        # The default strategy is a strategic merge patch
        api_response = v1.patch_namespaced_config_map(
            name='controller-config',
            namespace='gke-static-node-ip', # todo fix this
            body=patch_body
        )
        log_info(component, "updated controller-config")
        return api_response
    except client.exceptions.ApiException as e:
        log_error(component, "exception when patching ConfigMap controller-config")

def distributor():
    log_system("############## INITIALIZING GKE-STATIC-NODE-IP-DISTRIBUTOR ##############")
    config.load_incluster_config()
    nodes_data_parsed = get_process_raw_nodes_data_from_json()
    try:
        log_system("############## STARTING GKE-STATIC-NODE-IP-DISTRIBUTOR ##################")
        while True:
            update_cm_resource(nodes_data_parsed)
            nodes_data_parsed = monitor_update_nodes_data(nodes_data_parsed)
            time.sleep(60)
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        log_info(component, "control loop stopped")

if __name__ == "__main__":
    distributor()