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

import time
from functions import validate_ipv4, get_current_ip, get_vars_from_env
from fixer import change_node_ip
from logger import log_info, log_error

def controller():
    component = "controller"
    desired_ip, project_id, zone, network_tier = get_vars_from_env()
    try:
        while True:
            current_ip = get_current_ip()
            if not current_ip == desired_ip:
                log_error(component, f"found problem: current IP is {current_ip}, but desired is {desired_ip}")
                log_info(component, "sending request to fixer")
                change_node_ip(project_id, zone, network_tier, current_ip, desired_ip)
                log_info(component, "fixer finished")
            else:
                log_info(component, "current IP matches desired IP")
            time.sleep(5)
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        log_info(component, "control loop stopped")

if __name__ == "__main__":
    controller()