import threading
import time
import json
import random
from mqtt import MQTT
import yaml

def load_config(file_path="config/server_config.yaml"):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)

config = load_config()
id = config["server"]["id"]

clients = {}  # {client_id: status}

mqtt_client = MQTT(id)

def handle_message(topic, payload):
    global clients
    try:
        payload = json.loads(payload)
    except json.JSONDecodeError:
        print(f"[!] Failed to decode JSON from topic {topic}")
        return

    if topic.startswith("cluster/clients/announce"):
        client_id = payload["client_id"]
        clients[client_id] = "free"
        print(f"[+] New client: {client_id}")

    elif topic.startswith("cluster/clients/state"):
        client_id = payload["client_id"]
        status = payload["status"]
        clients[client_id] = status
        print(f"[*] Client {client_id} changed status to {status}")

    elif topic.startswith("cluster/tasks/result"):
        client_id = topic.split("/")[-1]
        print(f"[✓] Client {client_id} finished task: {payload['result']}")
        clients[client_id] = "free"

def task_sender():
    while True:
        time.sleep(5)
        free_clients = [cid for cid, status in clients.items() if status == "free"]
        if free_clients:
            client_id = random.choice(free_clients)
            task = {
                "pcap_file": "handshake.cap",
                "dict_file": "rockyou.txt",
                "bssid": "AA:BB:CC:DD:EE:FF"
            }
            mqtt_client.publish(f"cluster/tasks/assign/{client_id}", json.dumps(task))
            clients[client_id] = "busy"
            print(f"[>] Task pushed to client {client_id}")

def main():
    mqtt_client.connect()
    mqtt_client.subscribe("cluster/clients/announce")
    mqtt_client.subscribe("cluster/clients/state/#")
    mqtt_client.subscribe("cluster/tasks/result/#")

    threading.Thread(target=task_sender, daemon=True).start()

    while True:
        msg = mqtt_client.get_message()
        if msg:
            topic, payload = msg
            handle_message(topic, payload)
        time.sleep(0.1)

if __name__ == "__main__":
    main()
