import json
import os
import subprocess
import datetime
from dataclasses import dataclass
from pprint import pprint
from typing import Literal, Optional

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
    rsh: str = ""
    verbose: int = 0
    name: Optional[str] = None
    units: str = "GB"

    def __post_init__(self):
        # Clean up arguments
        if self.units not in UNITS.keys():
            raise ValueError(f"Unknown units {self.units} were used")

        # Parse name
        if self.name is None:
            self.name = self.repo

        # Make state topic
        self.slug = slugify(self.name, separator="_")
        self.state_topic = f"borg/{self.slug}/state"

    def _ask_borg(self, command: Literal["info", "list"]):
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

        if self.rsh != "":
            env["BORG_RSH"] = self.rsh

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

        date_format_code = "%Y-%m-%dT%H:%M:%S.%f"

        # Parse through it all
        scale = UNITS[self.units]
        cache_stats = repo_info["cache"]["stats"]
        info = {
            "location": repo_info["repository"]["location"],
            "id": repo_info["repository"]["id"],
            "chunks_unique": cache_stats["total_unique_chunks"],
            "chunks_total": cache_stats["total_chunks"],
            "size_dedup": round(float(cache_stats["unique_size"]) * scale, 8),
            "size_dedup_comp": round(
                float(cache_stats["unique_csize"]) * scale,
                8,
            ),
            "size_og": round(float(cache_stats["total_size"]) * scale, 8),
            "size_og_comp": round(float(cache_stats["total_csize"]) * scale, 8),
            "num_backups": len(repo_list["archives"]),
            # Time is returned in local time,
            # but is missing the timezone offset on the stamp
            # HA needs timestamp in ISO 8601 format with timezone
            "most_recent": datetime.datetime.strptime(
                repo_list["repository"]["last_modified"], date_format_code
            )
            .astimezone()
            .isoformat(),
        }
        return info

    def update(self, mqtt: MQTTSettings):
        """Send all updated info over MQTT"""

        if self.verbose >= 1:
            print(f"[{APP_NAME}][{self.name}] Getting update information")

        info = self._get_updates()

        if self.verbose >= 1:
            print(f"[{APP_NAME}][{self.name}] Sending MQTT update")

        if self.verbose >= 2:
            print(
                f"[{APP_NAME}][{self.name}] Payload for send to MQTT: {json.dumps(info)}"
            )

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
            payload["default_entity_id"] = f"{self.slug}_{key}"
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
