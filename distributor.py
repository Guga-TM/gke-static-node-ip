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
    
    return nodes.items

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
        node_name = node.metadata.name
        this_nodepool_assignment_config[node_name]['desired_ip'] = ips.pop()
        this_nodepool_assignment_config[node_name]['gcp_zone'] = get_zone_of_k8s_node(node_name)
    return this_nodepool_assignment_config

def get_process_nodes_data_from_json():
    # get data for all nodes from json
    json_data_env = os.environ['NODES_DATA_RAW']
    nodes_data_raw = json.loads(json_data_env)

    nodes_data_parsed = {}

    for nodepool in nodes_data_raw:
        desired_ips = nodes_data_raw[nodepool]
        desired_ips_set = set(desired_ips)
        nodes = get_k8s_nodes_from_nodepool(nodepool)
        nodes_data_parsed |= assign_ips_to_nodes(nodes, desired_ips_set)
    
    print(nodes_data_parsed)

def distributor():
    log_system("############## INITIALIZING GKE-STATIC-NODE-IP-DISTRIBUTOR ##############")
    config.load_incluster_config()
    get_process_nodes_data_from_json()
    try:
        log_system("############## STARTING GKE-STATIC-NODE-IP-DISTRIBUTOR ##################")
        while True:
            time.sleep(15)
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        log_info(component, "control loop stopped")

if __name__ == "__main__":
    distributor()