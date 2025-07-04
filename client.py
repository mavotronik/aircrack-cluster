import threading
import time
import json
import random
from mqtt import MQTT
import yaml
from aircrack_runner import analyze_and_run_aircrack
import psutil
import logging


def load_config(file_path="config/client_config.yaml"):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)

config = load_config()
id = config["client"]["id"]
hs_dir = config["paths"]["hs_dir"]
dict_dir = config["paths"]["dict_dir"]
loglevel_str = config["logs"]["level"].upper()

clients = {}  # {client_id: status}

CLIENT_ID = id
clients_state_topic = "cluster/clients/state"
announce_topic = "cluster/clients/announce"
task_topic = f"cluster/tasks/assign/{CLIENT_ID}"
result_topic = f"cluster/tasks/result/{CLIENT_ID}"

mqtt_client = MQTT(id)

logger = logging.getLogger("client")
loglevel = getattr(logging, loglevel_str, logging.INFO)
logger.setLevel(loglevel)

file_handler = logging.FileHandler("client.log", encoding="utf-8")
formatter = logging.Formatter('%(filename)s %(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.propagate = False 

def send_system_stats():
    while True:
        stats = {
            "client_id": id,
            "cpu": psutil.cpu_percent(),
            "ram": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage("/").percent
        }
        mqtt_client.publish("cluster/clients/stats", json.dumps(stats))
        time.sleep(15)

def do_task(task):
    mqtt_client.publish(clients_state_topic, json.dumps({
        "client_id": CLIENT_ID,
        "status": "busy"
    }))


    pcap_path = f"{hs_dir}/{task['pcap_file']}"
    dict_path = f"{dict_dir}/{task['dict_file']}"
    print(f"[{CLIENT_ID}] Starting task... pcap: {pcap_path} dict: {dict_path}")
    logger.info(f"[{CLIENT_ID}] Starting task... pcap: {pcap_path} dict: {dict_path}")

    result = analyze_and_run_aircrack(pcap_path, dict_path)

    mqtt_client.publish(result_topic, json.dumps({
        "result": result
    }))

    mqtt_client.publish(clients_state_topic, json.dumps({
        "client_id": CLIENT_ID,
        "status": "free"
    }))
    print(f"[{CLIENT_ID}] Finished task: {result}")
    logger.info(f"[{CLIENT_ID}] Finished task: {result}")


def handle_message(topic, payload):
    if topic == task_topic:
        task = json.loads(payload)
        print(f"[{CLIENT_ID}] Task received: {task}")
        logger.info(f"[{CLIENT_ID}] Task received: {task}")
        threading.Thread(target=do_task, args=(task,), daemon=True).start()

def announce_loop():
    while True:
        mqtt_client.publish(announce_topic, json.dumps({
            "client_id": CLIENT_ID
        }))
        logger.info(f"[♥] Announce published: {CLIENT_ID}")
        time.sleep(10)

def main():
    mqtt_client.connect()
    mqtt_client.subscribe(task_topic)

    threading.Thread(target=announce_loop, daemon=True).start()
    threading.Thread(target=send_system_stats, daemon=True).start()

    while True:
        msg = mqtt_client.get_message()
        if msg:
            topic, payload = msg
            handle_message(topic, payload)
        time.sleep(0.1)

if __name__ == "__main__":
    main()
    logging.info("Client: HELLO!")
