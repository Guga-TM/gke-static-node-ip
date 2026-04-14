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

component = os.path.splitext(os.path.basename(__file__))[0]

# Update existing access config
def update_access_config(
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

    try:
        operation = client.update_access_config(
            project=project_id,
            zone=zone,
            instance=instance,
            network_interface=network_interface_name,
            access_config_resource=access_config
        )
    except exceptions.BadRequest as google_exception:
        log_error(component, google_exception)
        raise exceptions.BadRequest(google_exception)
    except exceptions.ClientError as google_exception:
        log_error(component, google_exception)
        raise exceptions.ClientError(google_exception)
    except exceptions.GoogleAPICallError as google_exception:
        log_error(component, google_exception.message)
        raise exceptions.GoogleAPICallError(google_exception)

    log_info(component, f"setting IP address {ip_to_set} to {instance}...")
    try:
        operation.result()
        log_system("desired IP address set successfully")
    except exceptions.BadRequest as google_exception:
        log_error(component, google_exception)
        log_error(component, "Desired IP is not available, will try to fix next time")

def change_node_ip(
    instance_name,
    zone,
    desired_ip
):
    log_system(f"fixer got request to change IP of {instance_name} to {desired_ip}")
    
    # these variables were already validated
    project_id = os.environ['PROJECT_ID']
    network_tier = os.environ['NETWORK_TIER']

    # trying to update to desired ip
    update_access_config(
        project_id=project_id,
        network_tier=network_tier,
        zone=zone,
        instance=instance_name,
        ip_to_set=desired_ip
    )