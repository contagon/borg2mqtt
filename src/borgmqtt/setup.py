import json

import slugify

from .utils import (MQTTSettings, RepoSettings, connect_mqtt_client,
                    get_repo_info)


def setup(repo_settings: RepoSettings, mqtt_settings: MQTTSettings):
    """Send all config MQTT messages to setup sensors"""
    client = connect_mqtt_client()

    ######## CONFIG FOR REPOSITORY INFORMATION #############
    slug = slugify(repo_settings.name, separator="_")
    repo = get_repo_info(repo_settings)

    payload_unique = {
        "chunks_total": {"name": "Chunks Total"},
        "chunks_unique": {"name": "Chunks Unique"},
        "location": {"name": "Location"},
        "id": {"name": "ID"},
        "most_recent": {"name": "Timestamp", "device_class": "timestamp"},
        "num_backups": {"name": "Total Backups"},
        "size_dedup": {"name": "Deduplicated Size", "unit_of_meas": "Gb"},
        "size_dedup_comp": {
            "name": "Compressed Deduplicated Size",
            "unit_of_meas": "Gb",
        },
        "size_og": {"name": "Original Size", "unit_of_meas": "Tb"},
        "size_og_comp": {"name": "Original Compressed Size", "unit_of_meas": "Tb"},
    }

    state_topic = f"borg/{slug}/state"
    device = {
        "identifiers": [repo["id"]],
        "name": repo_settings.name,
        "model": "Borg Repository",
        "manufacturer": "Borg",
    }
    payload_shared = {"state_topic": state_topic, "device": device}
    for key in repo.keys():
        topic = f"homeassistant/sensor/{slug}/{key}/config"
        payload = {**payload_unique[key], **payload_shared}
        payload["object_id"] = f"{slug}_{key}"
        payload["unique_id"] = f"{slug}_{key}"
        payload["value_template"] = f"{{{{value_json.{key}}}}}"

        client.publish(topic, json.dumps(payload), retain=True)

    client.publish(state_topic, json.dumps(repo), retain=True)
