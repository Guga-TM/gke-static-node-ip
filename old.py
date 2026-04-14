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

# Some functions that are not used anymore

############ from fixer.py ####################################

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