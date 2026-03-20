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

import os
from google.cloud import compute_v1
from google.api_core import exceptions
from logger import log_info, log_error, log_system
from functions import get_vars_from_env

component = os.path.splitext(os.path.basename(__file__))[0]

def get_single_instance_by_external_ip(
    project_id: str,
    zone: str,
    ip: str
):
    client = compute_v1.InstancesClient()

    # Initialize request arguments
    request = compute_v1.ListInstancesRequest(
        project=project_id,
        zone=zone
    )

    # List all instances in the zone
    response = client.list(request=request)
    
    # Find instance with IP and return name only
    for instance in response :
        for network_interface in instance.network_interfaces:
            for access_config in network_interface.access_configs:
                if access_config.nat_i_p == ip:
                    return instance.name, access_config.name
        
    return -1, -1

# We don't know if access config name is set to its default value
def delete_access_config(
    project_id: str,
    zone: str,
    instance: str,
    current_access_config_name: str,
    network_interface_name: str = "nic0"
):
    client = compute_v1.InstancesClient()

    # Initialize request argument(s)
    request = compute_v1.DeleteAccessConfigInstanceRequest(
        access_config=current_access_config_name,
        instance=instance,
        network_interface=network_interface_name,
        project=project_id,
        zone=zone
    )

    # Make the request
    operation = client.delete_access_config(request=request)

    log_info(component, f"deleting External IP (access config) for {instance}...")
    operation.result()
    log_info(component, f"deleted successfully.")

def add_access_config_random_ip(
    project_id: str,
    network_tier: str,
    zone: str,
    instance: str,
    network_interface_name: str = "nic0"
):
    client = compute_v1.InstancesClient()
    
    # Define the access configuration
    access_config = compute_v1.AccessConfig()
    access_config.network_tier = network_tier

    operation = client.add_access_config(
        project=project_id,
        zone=zone,
        instance=instance,
        network_interface=network_interface_name,
        access_config_resource=access_config
    )

    log_info(component, f"setting random IP address to {instance}...")
    try:
        operation.result()
        log_info(component, f"successfully set random IP address. Will try to change it to desired on the next run")
    except exceptions.BadRequest as google_exception:
        log_error(component, "failed to assign random IP address, see error below")
        raise exceptions.BadRequest(google_exception)



# New Access Config will be created
# with a default name "External NAT"
def add_access_config(
    project_id: str,
    network_tier: str,
    zone: str,
    instance: str,
    ip_to_set: str = "random",
    network_interface_name: str = "nic0"
):
    client = compute_v1.InstancesClient()
    
    # Define the access configuration
    access_config = compute_v1.AccessConfig()
    access_config.network_tier = network_tier
    access_config.nat_i_p = ip_to_set

    operation = client.add_access_config(
        project=project_id,
        zone=zone,
        instance=instance,
        network_interface=network_interface_name,
        access_config_resource=access_config
    )

    log_info(component, f"setting IP address {ip_to_set} to {instance}...")
    try:
        operation.result()
        log_system("desired IP address set successfully")
    except exceptions.BadRequest as google_exception:
        log_error(component, google_exception)
        log_error(component, "Desired IP is not available, assigning random IP")
        add_access_config_random_ip(project_id, network_tier, zone, instance)

def change_node_ip(
    project_id,
    zone,
    network_tier,
    instance_name,
    desired_ip
):
    log_system(f"fixer got request to change IP of {instance_name} to {desired_ip}")
    
    project_id, zone, network_tier = get_vars_from_env()

    # todo 
    # get access config
    # check if deletion is needed

    delete_access_config(
        project_id=project_id,
        zone=zone,
        instance=instance_name,
        current_access_config_name=access_config_name
    )

    add_access_config(
        project_id=project_id,
        network_tier=network_tier,
        zone=zone,
        instance=instance_name,
        ip_to_set=desired_ip
    )