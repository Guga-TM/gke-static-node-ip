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

from google.cloud import compute_v1
import os

def get_single_instance_by_external_ip(
    project_id: str,
    zone: str,
    ip: str
):
    client = compute_v1.InstancesClient()
    
    # Filter for the specific external IP
    instance_filter = f'networkInterfaces.accessConfigs.natIP={ip}'
    
    # List instances with the filter
    response = client.list(project=project_id, zone=zone, filter=instance_filter)
    
    # Extract only the names
    for instance in response :
        print(f"Found instance {instance}")
        return instance.name # should be 'instance.id' probably
        
    return -1

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

    print(f"Deleting External IP (access config) for {instance_name}...")
    operation.result()
    print(f"Deleted successfully.")
    print(operation)

# New Access Config will be created
# with a default name "External NAT"
def add_access_config(
    project_id: str,
    network_tier: str,
    zone: str,
    instance: str,
    ip_to_set: str,
    network_interface_name: str = "nic0"
):
    client = compute_v1.InstancesClient()
    
    # Define the access configuration
    access_config = compute_v1.AccessConfig()
    access_config.network_tier = network_tier

    operation = client.add_access_config(
        project=project_id,
        zone=zone,
        instance=instance_name,
        network_interface=network_interface_name,
        access_config_resource=access_config
    )

    print(f"Setting IP address {ip_to_set} to {instance_name}...")
    operation.result()
    print(f"IP address set successfully.")
    print(operation)


def change_node_ip(current_ip, desired_ip):
    project_id = os.environ['PROJECT_ID']
    network_tier = os.environ['NETWORK_TIER']
    zone = os.environ['ZONE']
    instance = get_single_instance_by_external_ip(project_id, zone, current_ip)
    delete_access_config(
        project_id=project_id,
        zone=zone,
        instance=instance
    )
    add_access_config(
        project_id=project_id,
        network_tier=network_tier,
        zone=zone,
        instance=instance,
        ip_to_set=desired_ip
    )