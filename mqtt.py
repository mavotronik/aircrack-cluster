import yaml
import paho.mqtt.client as mqtt
from typing import Dict, Optional
from queue import Queue

def load_config(file_path="config/mqtt_config.yaml"):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)

config = load_config()

class MQTT:
    def __init__(self, id):
        self.broker = config["mqtt"]["broker"]
        self.port = config["mqtt"]["port"]
        self.username = config["mqtt"]["username"]
        self.password = config["mqtt"]["password"]
        self.id = (id)

        self.client = mqtt.Client(client_id=self.id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.message_queue = Queue()

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected to MQTT broker with code: {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        # print(f"Received: [Topic: {topic}] -> {payload}")
        self.message_queue.put((topic, payload))

    def connect(self):
        try:
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            print(f"MQTT connection error: {e}")

    def subscribe(self, topic, qos=0):
        self.client.subscribe(topic, qos)
        print(f"Subscribed to {topic}")

    def publish(self, topic, payload):
        self.client.publish(topic=topic, payload=payload)
        print(f"Published to: {topic} with payload: {payload}")

    def get_message(self) -> Optional[tuple]:
        if not self.message_queue.empty():
            return self.message_queue.get()
        return None
