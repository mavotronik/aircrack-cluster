import threading
import time
import json
import random
from mqtt import MQTT
import yaml
from task_manager import watch_loop
from web import run_flask_app

def load_config(file_path="config/server_config.yaml"):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)

config = load_config()
id = config["server"]["id"]

clients = {}  # {client_id: status}
task_queue = []
clients_info = {}

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
        if client_id not in clients:
            clients[client_id] = "free"
            print(f"[+] New client: {client_id}")
        else:
            print(f"[♥] Heartbeat from client: {client_id}")
            # clients[client_id] = "free"

    elif topic.startswith("cluster/clients/state"):
        client_id = payload["client_id"]
        status = payload["status"]
        clients[client_id] = status
        print(f"[*] Client {client_id} changed status to {status}")

    elif topic.startswith("cluster/tasks/result"):
        client_id = topic.split("/")[-1]
        print(f"[✓] Client {client_id} finished task: {payload['result']}")
        clients[client_id] = "free"

    elif topic == "cluster/clients/stats":
        data = json.loads(payload)
        client_id = data["client_id"]
        clients_info[client_id] = {
            "cpu": data["cpu"],
            "ram": data["ram"],
            "disk": data["disk"],
            "last_seen": time.time()
        }

def task_sender():
    while True:
        time.sleep(2)

        if not task_queue:
            continue

        free_clients = [cid for cid, status in clients.items() if status == "free"]
        if not free_clients:
            continue

        task = task_queue.pop(0)  # get task from queue
        client_id = random.choice(free_clients)

        # Send task without BSSID, client will find itself
        mqtt_client.publish(
            f"cluster/tasks/assign/{client_id}",
            json.dumps(task)
        )
        clients[client_id] = "busy"
        print(f"[>] Task sent to client {client_id}: {task['pcap_file']}")

def on_new_file_detected(filepath):
    task = {
        "pcap_file": filepath,
        "dict_file": "dicts/cracked.txt"
    }
    task_queue.append(task)
    print(f"[+] Task added for file: {filepath}")

def main():
    mqtt_client.connect()
    mqtt_client.subscribe("cluster/clients/announce")
    mqtt_client.subscribe("cluster/clients/state/#")
    mqtt_client.subscribe("cluster/tasks/result/#")


    threading.Thread(target=task_sender, daemon=True).start()
    threading.Thread(target=watch_loop, args=(on_new_file_detected,), daemon=True).start()
    threading.Thread(target=run_flask_app, args=(clients,), daemon=True).start()

    while True:
        msg = mqtt_client.get_message()
        if msg:
            topic, payload = msg
            handle_message(topic, payload)
        time.sleep(0.1)

if __name__ == "__main__":
    main()
