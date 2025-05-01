import threading
import time
import json
import paho.mqtt.client as mqtt
import random

CLIENT_ID = f"client_{random.randint(1000,9999)}"  # random id for tests
BROKER = "localhost"
PORT = 1883

def on_connect(client, userdata, flags, rc):
    print(f"{CLIENT_ID} connected to broker")
    client.subscribe(f"cluster/tasks/assign/{CLIENT_ID}")

def on_message(client, userdata, msg):
    task = json.loads(msg.payload.decode())
    print(f"[{CLIENT_ID}] Task recieved: {task}")

    # Simulate aircrack-ng work
    threading.Thread(target=do_task, args=(task,), daemon=True).start()

def do_task(task):
    client.publish("cluster/clients/state", json.dumps({
        "client_id": CLIENT_ID,
        "status": "busy"
    }))

    print(f"[{CLIENT_ID}] Starting task...")
    time.sleep(random.randint(5, 10))  # simlate
    result = random.choice(["KEY FOUND!", "KEY NOT FOUND", "INCORRECT HASH"])

    client.publish(f"cluster/tasks/result/{CLIENT_ID}", json.dumps({
        "result": result
    }))

    client.publish("cluster/clients/state", json.dumps({
        "client_id": CLIENT_ID,
        "status": "free"
    }))
    print(f"[{CLIENT_ID}] Finished task: {result}")

client = mqtt.Client(client_id=CLIENT_ID)
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, keepalive=60)

# Announce on start
def announce():
    while True:
        client.publish("cluster/clients/announce", json.dumps({
            "client_id": CLIENT_ID
        }))
        time.sleep(10)

threading.Thread(target=announce, daemon=True).start()

client.loop_forever()
