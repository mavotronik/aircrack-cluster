import threading
import time
import json
import random
import paho.mqtt.client as mqtt

clients = {}  # {client_id: status}

BROKER = "localhost"  # IP or hostname of MQTT broker
PORT = 1883

def on_connect(client, userdata, flags, rc):
    print("Server connected to broker")
    client.subscribe("cluster/clients/announce")
    client.subscribe("cluster/clients/state/#")
    client.subscribe("cluster/tasks/result/#")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = json.loads(msg.payload.decode())

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
        time.sleep(5)  # Check if any tasks every 5 secs
        free_clients = [cid for cid, status in clients.items() if status == "free"]
        if free_clients:
            client_id = random.choice(free_clients)
            task = {
                "pcap_file": "handshake.cap",
                "dict_file": "rockyou.txt",
                "bssid": "AA:BB:CC:DD:EE:FF"
            }
            client.publish(f"cluster/tasks/assign/{client_id}", json.dumps(task))
            clients[client_id] = "busy"
            print(f"[>] Task pushed to client {client_id}")

client = mqtt.Client(client_id="server")
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, keepalive=60)

# Start thread to send tsks to clients
threading.Thread(target=task_sender, daemon=True).start()

client.loop_forever()
