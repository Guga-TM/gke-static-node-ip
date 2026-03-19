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

import requests, os, time
from functions import validate_ipv4
from fixer import change_node_ip
from logger import log_info, log_error

component = os.path.splitext(os.path.basename(__file__))[0]

def get_current_ip():
    # ip checker address
    log_info(component, "sending request to ipinfo.io to check current IP...")
    url = 'https://ipinfo.io'
    response = requests.get(url)

    # convert response to json
    ipinfo_data = response.json()
    current_ip = ipinfo_data['ip']

    # use IP validator function to check current ip string
    log_info(component, "checking current IP format validity...")
    validate_ipv4(current_ip)

    return current_ip

def get_desired_ip():
    # get value from env variable
    desired_ip = os.environ['DESIRED_IP']

    # use IP validator function to check desired ip string
    log_info(component, "checking desired IP format validity...")
    validate_ipv4(desired_ip)

    return desired_ip

def controller():
    try:
        while True:
            current_ip = get_current_ip()
            desired_ip = get_desired_ip()
            if not current_ip == desired_ip:
                log_error(component, f"found problem: current IP is {current_ip}, but desired is {desired_ip}")
                log_info(component, "sending request to fixer")
                change_node_ip(current_ip, desired_ip)
                log_info(component, "fixer succeeded")
            time.sleep(1)
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        log_info(component, "control loop stopped")

if __name__ == "__main__":
    controller()