import json
import os
import subprocess
import time
from dataclasses import dataclass
from pprint import pprint

import paho.mqtt.publish as publish
from slugify import slugify

from .const import APP_NAME, UNITS


@dataclass
class MQTTSettings:
    host: str = "localhost"
    port: int = 1883
    user: str = ""
    password: str = ""


@dataclass
class Repository:
    repo: str
    key: str = ""
    verbose: int = 0
    name: str = None
    units: str = "GB"

    def __post_init__(self):
        # Clean up arguments
        if self.units not in UNITS.keys():
            raise ValueError(f"Unknown units {self.units} were used")

        if self.verbose is None:
            self.verbose = 0

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

        if self.verbose >= 2:
            print(f"[{APP_NAME}][{self.name}] Running {' '.join(arguments)}")

        result = subprocess.run(arguments, stdout=subprocess.PIPE, env=env)
        result = json.loads(result.stdout)

        if self.verbose >= 3:
            print(f"[{APP_NAME}][{self.name}] Got back")
            pprint(result)

        return result

    def _get_updates(self):
        """Ask borg for information and parse the results"""

        # Ask borg for all info
        repo_info = self._ask_borg("info")
        repo_list = self._ask_borg("list")

        # Time is returned in local time,
        # but is missing the timezone offset on the stamp
        # https://stackoverflow.com/a/3168394
        is_dst = time.daylight and time.localtime().tm_isdst > 0
        utc_offset = int((time.altzone if is_dst else time.timezone) / (3600))

        # Parse through it all
        info = {
            "location": repo_info["repository"]["location"],
            "id": repo_info["repository"]["id"],
            "chunks_unique": repo_info["cache"]["stats"]["total_unique_chunks"],
            "chunks_total": repo_info["cache"]["stats"]["total_chunks"],
            "size_dedup": round(
                float(repo_info["cache"]["stats"]["unique_size"]) * UNITS[self.units], 2
            ),
            "size_dedup_comp": round(
                float(repo_info["cache"]["stats"]["unique_csize"]) * UNITS[self.units],
                2,
            ),
            "size_og": round(
                float(repo_info["cache"]["stats"]["total_size"]) * UNITS[self.units], 2
            ),
            "size_og_comp": round(
                float(repo_info["cache"]["stats"]["total_csize"]) * UNITS[self.units], 2
            ),
            "num_backups": len(repo_list["archives"]),
            "most_recent": repo_list["archives"][-1]["time"] + f"-{utc_offset:02d}:00",
        }

        return info

    def update(self, mqtt: MQTTSettings):
        """Send all updated info over MQTT"""

        if self.verbose >= 1:
            print(f"[{APP_NAME}][{self.name}] Getting update information")

        info = self._get_updates()

        if self.verbose >= 1:
            print(f"[{APP_NAME}][{self.name}] Sending MQTT update")

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

        if self.verbose >= 1:
            print(f"[{APP_NAME}][{self.name}] Getting setup information")

        # Get all information from repository
        info = self._get_updates()

        # Things unique to each sensor
        payload_unique = {
            "chunks_total": {"name": "Chunks Total"},
            "chunks_unique": {"name": "Chunks Unique"},
            "location": {"name": "Location", "enabled_by_default": False},
            "id": {"name": "ID", "enabled_by_default": False},
            "most_recent": {"name": "Timestamp", "device_class": "timestamp"},
            "num_backups": {"name": "Total Backups"},
            "size_dedup": {
                "name": "Dedup Size",
                "device_class": "data_size",
                "unit_of_meas": self.units,
            },
            "size_dedup_comp": {
                "name": "Dedup Compressed Size",
                "device_class": "data_size",
                "unit_of_meas": self.units,
            },
            "size_og": {
                "name": "Original Size",
                "device_class": "data_size",
                "unit_of_meas": self.units,
            },
            "size_og_comp": {
                "name": "Original Compressed Size",
                "device_class": "data_size",
                "unit_of_meas": self.units,
            },
        }

        device = {
            "identifiers": [info["id"]],
            "name": self.name,
            "model": "Borg Repository",
            "manufacturer": "Borg",
        }
        payload_shared = {"state_topic": self.state_topic, "device": device}

        if self.verbose >= 1:
            print(f"[{APP_NAME}][{self.name}] Sending MQTT setup msgs")

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
