import json
import os
import subprocess
from dataclasses import dataclass
from pprint import pprint

import paho.mqtt.publish as publish
from slugify import slugify


@dataclass
class MQTTSettings:
    host: str = "localhost"
    port: int = 1883
    user: str = ""
    password: str = ""


@dataclass
class Repository:
    repo: str
    key: str
    verbose: bool = False
    name: str = None

    def __post_init__(self):
        # Parse name
        if self.name is None:
            self.name = self.repo

        # Make state topic
        self.slug = slugify(self.name, separator="_")
        self.state_topic = f"borg/{self.slug}/state"

    def _ask_borg(self, command):
        """Poll borg for a response"""

        env = os.environ.copy()
        env["BORG_PASSPHRASE"] = self.key

        # Get info about all repos
        arguments = [
            "borg",
            command,
            self.repo,
            "--json",
        ]

        if self.verbose:
            print(f"[BORGMQTT][{self.name}] Running {' '.join(arguments)}")

        result = subprocess.run(arguments, stdout=subprocess.PIPE, env=env)
        result = json.loads(result.stdout)

        if self.verbose:
            print("[BORGMQTT][{self.name}] Got back")
            pprint(result)

        return result

    def _get_updates(self):
        """Get all info from borgmatic list & borgmatic info commands"""

        # Ask borg for all info
        repo_info = self._ask_borg("info")
        repo_list = self._ask_borg("list")

        # Parse through it all
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

    def update(self, mqtt: MQTTSettings):
        """Send all updated info over MQTT"""

        if self.verbose:
            print(f"[BORGMQTT][{self.name} Updating")

        info = self._get_updates()
        publish.single(
            self.state_topic,
            payload=json.dumps(info),
            hostname=mqtt.host,
            port=mqtt.port,
            auth={"username": mqtt.user, "password": mqtt.password},
            retain=True,
        )

    def setup(self, mqtt: MQTTSettings):
        """Send MQTT autodiscovery message"""

        if self.verbose:
            print(f"[BORGMQTT][{self.name} Setting up")

        # Get all information from repository
        info = self._get_updates()

        # Things unique to each sensor
        payload_unique = {
            "chunks_total": {"name": "Chunks Total"},
            "chunks_unique": {"name": "Chunks Unique"},
            "location": {"name": "Location"},
            "id": {"name": "ID"},
            "most_recent": {"name": "Timestamp", "device_class": "timestamp"},
            "num_backups": {"name": "Total Backups"},
            "size_dedup": {
                "name": "Deduplicated Size",
                "device_class": "data_size",
                "unit_of_meas": "GB",
            },
            "size_dedup_comp": {
                "name": "Compressed Deduplicated Size",
                "device_class": "data_size",
                "unit_of_meas": "GB",
            },
            "size_og": {
                "name": "Original Size",
                "device_class": "data_size",
                "unit_of_meas": "TB",
            },
            "size_og_comp": {
                "name": "Original Compressed Size",
                "device_class": "data_size",
                "unit_of_meas": "TB",
            },
        }

        device = {
            "identifiers": [info["id"]],
            "name": self.name,
            "model": "Borg Repository",
            "manufacturer": "Borg",
        }
        payload_shared = {"state_topic": self.state_topic, "device": device}

        for key in info.keys():
            topic = f"homeassistant/sensor/{self.slug}/{key}/config"
            payload = {**payload_unique[key], **payload_shared}
            payload["object_id"] = f"{self.slug}_{key}"
            payload["unique_id"] = f"{self.slug}_{key}"
            payload["value_template"] = f"{{{{value_json.{key}}}}}"

            publish.single(
                topic,
                payload=json.dumps(payload),
                hostname=mqtt.host,
                port=mqtt.port,
                auth={"username": mqtt.user, "password": mqtt.password},
                retain=True,
            )
