import json
import os
import subprocess
from dataclasses import dataclass

import paho.mqtt.client as paho

BROKER_ADDRESS = "localhost"
BROKER_PORT = 1883
BROKER_USER = ""
BROKER_PASSWORD = ""


@dataclass
class RepoSettings:
    repo: str
    key: str
    name: str


@dataclass
class MQTTSettings:
    address: str = ""
    port: int = 1883
    user: str = ""
    password: str = ""


def get_repo_info(repo_settings: RepoSettings):
    """Get all info from borgmatic list & borgmatic info commands"""
    env = os.environ.copy()
    env["BORG_PASSPHRASE"] = repo_settings.key

    # Get info about all repos
    arguments = [
        "borg",
        "info",
        repo_settings.repo,
        "--json",
    ]
    result = subprocess.run(arguments, stdout=subprocess.PIPE, env=env)
    repo_info = json.loads(result.stdout)
    print(repo_info)

    # Get list about all repos
    arguments = [
        "borg",
        "list",
        repo_settings.repo,
        "--json",
    ]
    result = subprocess.run(arguments, stdout=subprocess.PIPE, env=env)
    repo_list = json.loads(result.stdout)

    # Get all info we need from the info/list
    info = {
        "location": repo_info["repository"]["location"],
        "id": repo_info["repository"]["id"],
        "chunks_unique": repo_info["cache"]["stats"]["total_unique_chunks"],
        "chunks_total": repo_info["cache"]["stats"]["total_chunks"],
        "size_dedup": round(
            float(repo_info["cache"]["stats"]["unique_size"]) / 10**9, 2
        ),
        "size_dedup_comp": round(
            float(repo_info["cache"]["stats"]["unique_csize"]) / 10**9, 2
        ),
        "size_og": round(
            float(repo_info["cache"]["stats"]["total_size"]) / 10**12, 2
        ),
        "size_og_comp": round(
            float(repo_info["cache"]["stats"]["total_csize"]) / 10**12, 2
        ),
        "num_backups": len(repo_list["archives"]),
        "most_recent": repo_list["archives"][-1]["time"] + "-04:00",
    }

    return info


def connect_mqtt_client(mqtt_settings: MQTTSettings):
    """CONNECT TO MQTT Broker"""

    def on_publish(client, userdata, mid):
        print("on_publish, mid {}".format(mid))
        print(client)
        print(userdata)
        print(mid)

    def on_log(client, userdata, level, buf):
        if "home" in buf:
            start = buf.find("homeassistant")
        else:
            start = buf.find("borg")
        end = buf.find("''")
        topic = buf[start:end]
        print(f"[BORGMQTT] Sent message to {topic}")

    client = paho.Client("backups")
    client.username_pw_set(mqtt_settings.user, password=mqtt_settings.password)
    client.connect(mqtt_settings.address, mqtt_settings.port)
    # client.on_publish = on_publish
    client.on_log = on_log
    return client
