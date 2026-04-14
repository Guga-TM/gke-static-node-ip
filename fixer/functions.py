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

import ipaddress, os
from logger import log_info, log_error
from google.cloud import compute_v1, resourcemanager_v3
from google.api_core import exceptions

def get_instance_current_ip(
    project_id: str,
    zone: str,
    instance: str
):
    client = compute_v1.InstancesClient()

    # Initialize request arguments
    request = compute_v1.GetInstanceRequest(
        project=project_id,
        zone=zone,
        instance=instance
    )

    # Get instance info
    try:
        response = client.get(request=request)
     except exceptions.BadRequest as google_exception:
        log_error(component, google_exception)
        raise exceptions.BadRequest(google_exception)
    except exceptions.ClientError as google_exception:
        log_error(component, google_exception)
        raise exceptions.ClientError(google_exception)
    except exceptions.GoogleAPICallError as google_exception:
        log_error(component, google_exception.message)
        raise exceptions.GoogleAPICallError(google_exception)
    
    access_configs_found = 0
    access_config_ip = ""

    # Loop through network interfaces and access configs to find the NAT IP (External IP)
    for network_interface in response.network_interfaces:
        for access_config in network_interface.access_configs:
            access_configs_found += 1
            access_config_ip = access_config.nat_i_p

    if access_configs_found == 0:
        log_error(component, f"access configs not found for instance {instance}")
        access_config_ip = "-1"
        
    if access_configs_found > 1:
        log_error(component, f"found more access configs for {instance} than expected: {access_configs_found}")
        access_config_ip = "-1"
        
    return access_config_ip

def check_project_validity(project_id):
    component = "gcp_project_id_validator"
    try:
        # Create the client
        client = resourcemanager_v3.ProjectsClient()
        
        # The resource name must be in the format "projects/{project_id}"
        project_name = f"projects/{project_id}"
        
        # Attempt to get the project
        project = client.get_project(name=project_name)

        return True

    except exceptions.NotFound:
        log_error(component, f"project not found: {project_id}")
        raise exceptions.NotFound
    except exceptions.Forbidden:
        log_error(component, f"access forbidden (project exists, but you lack permissions): {project_id}")
        raise exceptions.Forbidden
    except Exception as e:
        log_error(component, f"an error occurred: {e}")
        raise Exception

def validate_gcp_zone(project_id, zone_name):
    component = "gcp_zone_validator"
    # Initialize the zones client
    zones_client = compute_v1.ZonesClient()
    
    # List all zones in the project
    request = compute_v1.ListZonesRequest(project=project_id)
    zones = zones_client.list(request=request)
    
    # Check if the zone_name exists in the list of valid zones
    for zone in zones:
        if zone.name == zone_name and zone.status == "UP":
            return True

    log_error(component, f"Invalid GCP zone name, got {zone_name}")  
    raise ValueError

def validate_gcp_network_tier(network_tier):
    component = "gcp_network_tier_validator"
    if network_tier not in ["PREMIUM", "STANDARD"]:
        log_error(component, f"unknown tier: {network_tier}")
        raise Exception
    
    return True

def validate_vars_from_env(zone):
    component = "env_vars_fetcher"
    # get values from env variables
    # and then check them using validator functions
    # zone variable got from controller

    project_id = os.environ['PROJECT_ID']
    log_info(component, "sending request to check GCP project id validity")
    check_project_validity(project_id)

    log_info(component, "sending request to check GCP zone validity")
    validate_gcp_zone(project_id, zone)

    network_tier = os.environ['NETWORK_TIER']
    log_info(component, "sending request to check GCP network tier validity")
    validate_gcp_network_tier(network_tier)