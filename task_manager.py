import os
import time
import yaml

def load_config(file_path="config/server_config.yaml"):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)

config = load_config()
PCAP_DIR = config["server"]["hs_dir"]

# PCAP_DIR = "pcaps"
KNOWN_FILES = set()

def find_new_tasks():
    global KNOWN_FILES
    new_tasks = []

    try:
        current_files = {
            f for f in os.listdir(PCAP_DIR)
            if f.endswith(".cap") or f.endswith(".pcap")
        }

        new_files = current_files - KNOWN_FILES
        for file in new_files:
            print(f"[+] New file found: {file}")
            new_tasks.append(os.path.join(PCAP_DIR, file))

        KNOWN_FILES.update(new_files)
        return new_tasks

    except FileNotFoundError:
        print(f"[!] Directory {PCAP_DIR} not found!")
        return []

def watch_loop(callback, poll_interval=5):
    while True:
        new_files = find_new_tasks()
        for filepath in new_files:
            callback(filepath)
        time.sleep(poll_interval)
