import subprocess
import re
from typing import Callable, Dict, Optional
import yaml
import logging


def load_config(file_path="config/server_config.yaml"):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)

config = load_config()
loglevel_str = config["logs"]["level"].upper()

logger = logging.getLogger("aircrack-runner")
loglevel = getattr(logging, loglevel_str, logging.INFO)
logger.setLevel(loglevel)

file_handler = logging.FileHandler("aircrack-runnerlog", encoding="utf-8")
formatter = logging.Formatter('%(filename)s %(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.propagate = False


def analyze_pcap(pcap_file: str) -> Optional[str]:
    """
    Первый запуск aircrack-ng для извлечения BSSID из pcap-файла.
    Возвращает BSSID, если найден хендшейк, иначе None.
    """
    process = subprocess.Popen(
        ['aircrack-ng', pcap_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    bssid = None

    try:
        for line in process.stdout:
            if "WPA" in line and "handshake" in line:
                bssid_match = re.search(r'^\s*\d+\s+([0-9A-Fa-f:]{17})', line)
                if bssid_match:
                    bssid = bssid_match.group(1)
                    print(f"Found BSSID: {bssid}")
                    break
    finally:
        process.stdout.close()
        process.stderr.close()

    return bssid


def run_aircrack(
    pcap_file: str,
    dict_file: str,
    bssid: str,
    progress_callback: Optional[Callable[[Dict], None]] = None
) -> str:
    """
    Запускает aircrack-ng и отслеживает прогресс атаки.
    Возвращает строку с результатом.
    """
    process = subprocess.Popen(
        ['aircrack-ng', pcap_file, '-w', dict_file, '-b', bssid],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    result = "UNKNOWN"

    try:
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                if progress_callback:
                    data = {}

                    progress_match = re.search(r'(\d+\.\d+)%', output)
                    if progress_match:
                        data["progress"] = float(progress_match.group(1))

                    speed_match = re.search(r'(\d+\.\d+) k/s', output)
                    if speed_match:
                        data["speed_kps"] = float(speed_match.group(1))

                    time_left_match = re.search(r'Time left:\s+(.*?)\s*$', output)
                    if time_left_match:
                        data["time_left"] = time_left_match.group(1)

                    if data:
                        progress_callback(data)

                success = re.search(r'KEY FOUND! \[(.*?)\]', output)
                no_success = re.search(r'KEY NOT FOUND', output)
                incorrect = re.search(r'No matching network found - check your bssid', output)

                if success:
                    result = f'KEY FOUND! [{success.group(1)}]'
                    break
                elif no_success:
                    result = 'KEY NOT FOUND'
                    break
                elif incorrect:
                    result = 'INCORRECT HASH'
                    break

    finally:
        process.stdout.close()
        process.stderr.close()
        return result


def analyze_and_run_aircrack(pcap_file: str, dict_file: str) -> str:
    """
    Анализирует pcap-файл, чтобы получить BSSID,
    затем запускает aircrack-ng с найденным BSSID.
    Результат сохраняется в файл {имя_файла.pcap}.txt
    """
    bssid = analyze_pcap(pcap_file)
    if not bssid:
        result = "NO HANDSHAKE FOUND"
    else:
        result = run_aircrack(pcap_file, dict_file, bssid)

    # Сохраняем результат
    result_filename = f"{pcap_file}.txt"
    try:
        with open(result_filename, "w") as f:
            f.write(result + "\n")
        print(f"[+] Result saved to {result_filename}")
        logger.info(f"[+] Result saved to {result_filename}")
    except IOError as e:
        print(f"[!] Failed to save result: {e}")
        logger.error(f"[!] Failed to save result: {e}")

    return result


# Пример вызова
if __name__ == "__main__":
    pcap_file = "uploads/handshake.pcap"
    dict_file = "dicts/cracked.txt"

    result = analyze_and_run_aircrack(pcap_file, dict_file)
    print(f"Result: {result}")
