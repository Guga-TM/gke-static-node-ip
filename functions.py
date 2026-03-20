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

import ipaddress, requests, os
from logger import log_info, log_error
from google.cloud import compute_v1, resourcemanager_v3
from google.api_core import exceptions

def validate_ipv4(ip_str):
    component = "ip_validator"
    try:
        ipaddress.IPv4Address(ip_str)
        return True
    except ValueError:
        log_error(component, f"Wrong IP address format, got {ip_str}")
        ipaddress.IPv4Address(ip_str)
        return False

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
            
    raise Exception(f"Invalid GCP zone name, got {zone_name}")

def validate_gcp_network_tier(network_tier):
    component = "gcp_network_tier_validator"
    if network_tier not in ["PREMIUM", "STANDARD"]:
        log_error(component, f"unknown tier: {network_tier}")
        raise Exception
    
    return True

def get_current_ip():
    component = "current_ip_fetcher"
    url = 'https://ipinfo.io'
    current_ip = ''
    log_info(component, "sending request to ipinfo.io to check current IP")

    for i in range(1, 6):
        try:
            response = requests.get(url, timeout=5)
            # convert response to json
            ipinfo_data = response.json()
            current_ip = ipinfo_data['ip']
        except requests.exceptions.Timeout:
            if i < 5:
                log_info(component, f"the request timed out, trying again - attempt {i}")
            else:
                log_error(component, "the request timed out 5 times, restarting application")
                raise requests.exceptions.Timeout

    # use IP validator function to check current ip string
    log_info(component, "sending request to check current IP format validity")
    validate_ipv4(current_ip)

    return current_ip

def get_vars_from_env():
    component = "env_vars_fetcher"
    # get values from env variables
    # and then check them using validator functions

    desired_ip = os.environ['DESIRED_IP']
    log_info(component, "sending request to check desired IP format validity")
    validate_ipv4(desired_ip)

    project_id = os.environ['PROJECT_ID']
    log_info(component, "sending request to check GCP project id validity")
    check_project_validity(project_id)

    zone = os.environ['ZONE']
    log_info(component, "sending request to check GCP zone validity")
    validate_gcp_zone(project_id, zone)

    network_tier = os.environ['NETWORK_TIER']
    log_info(component, "sending request to check GCP network tier validity")
    validate_gcp_network_tier(network_tier)

    return desired_ip, project_id, zone, network_tier