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
    desired_ip = data.get('desired_ip')
    try:
        change_node_ip(instance_name, desired_ip)
    except:
        return 500

    return 200

if __name__ == "__main__":
    app.run(port=6924)