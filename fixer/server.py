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

from flask import Flask, request
from fixer import change_node_ip
from functions import validate_vars_from_env, get_instance_current_ip
import signal, sys, os

app = Flask(__name__)

def handle_sigterm(signum, frame):
    print("Received SIGTERM, shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

@app.route("/")
def mainpage():
    return "Ok"

@app.route("/fix", methods=['POST'])
def process_fix_request():
    data = request.get_json()
    if not data:
        return "JSON data not found", 400

    instance_name = data.get('instance_name')
    zone = data.get('zone')
    desired_ip = data.get('desired_ip')
    try:
        change_node_ip(instance_name, zone, desired_ip)
    except:
        return "error in changing node IP", 500

    return "fix request completed", 200

@app.route("/startup", methods=['GET'])
def startup_probe():
    try:
        validate_vars_from_env()
        return "validated ok", 200
    except:
        return f"validation error", 500

@app.route("/ready", methods=['GET'])
def readiness_probe():
    return "application ready", 200

@app.route("/get_ip_of_node", methods=['POST'])
def process_get_ip_request():
    data = request.get_json()
    if not data:
        return "JSON data not found", 400

    instance = data.get('instance_name')
    zone = data.get('zone')
    project_id = os.environ['PROJECT_ID']
    try:
        current_ip = get_instance_current_ip(project_id, zone, instance)
        return current_ip, 200
    except:
        return f"error getting current IP of {instance}", 500
    

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=6924)