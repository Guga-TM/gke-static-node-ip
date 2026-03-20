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

import time, requests
from functions import get_current_ip
from logger import log_info, log_error, log_system

component = "controller"

def send_fix_request(instance_name, desired_ip):
    url = 'http://fixer:6924'
    data = {'instance_name': instance_name, 'desired_ip': desired_ip}

    # sending post request
    response = requests.post(url, json=data, timeout=180)

    status = response.status_code
    resp_data = response.text
    if status == '200' :
        log_info(component, "got response 200 from fixer")
    else:
        log_error(component, f"request to fixer API failed with {status} error")
        log_error(component, "check fixer error logs")

def controller():
    log_system("############## INITIALIZING GKE-STATIC-NODE-IP-CONTROLLER ##############")
    desired_ip = get_desired_ip()
    instance_name = os.environ['NODE_NAME']
    try:
        log_system("############## STARTING GKE-STATIC-NODE-IP-CONTROLLER ##################")
        while True:
            current_ip = get_current_ip()
            if not current_ip == desired_ip:
                log_error(component, f"found problem: current IP is {current_ip}, but desired is {desired_ip}")
                log_info(component, "sending request to fixer")
                send_fix_request(instance_name, desired_ip)
                log_system("end of fix loop on controller's side")
            else:
                log_info(component, "current IP matches desired IP")
            time.sleep(5)
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        log_info(component, "control loop stopped")

if __name__ == "__main__":
    controller()