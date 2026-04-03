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

from flask import Flask
from fixer import change_node_ip
import request

app = Flask(__name__)

@app.route("/")
def mainpage():
    return "Ok"

@app.route("/fix", , methods=['POST'])
def process_fix_request():
    data = request.get_json()
    if not data:
        return 400

    instance_name = data.get('instance_name')
    zone = data.get('zone')
    desired_ip = data.get('desired_ip')
    try:
        change_node_ip(instance_name, zone, desired_ip)
    except:
        return 500

    return 200

if __name__ == "__main__":
    app.run(port=6924)