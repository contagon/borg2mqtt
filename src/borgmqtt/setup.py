import json

from .utils import connect_mqtt_client


def setup():
    """Send all config MQTT messages to setup sensors"""
    client = connect_mqtt_client()

    ######## CONFIG FOR GENERAL TRACKING BINARY SENSORS #############
    # Misc properties that they all binary sensors use
    payload_shared = {
        "device": {
            "identifiers": ["borg", "tracker"],
            "name": "Borg Status Tracker",
            "model": "Borgmatic",
            "manufacturer": "Borg",
        }
    }

    payload_unique = {
        "prune": {"device_class": "running", "name": "Prune"},
        "create": {"device_class": "running", "name": "Create"},
        "check": {"device_class": "running", "name": "Check"},
        "error": {"device_class": "problem", "name": "Error"},
    }
    for key in payload_unique.keys():
        topic = f"homeassistant/binary_sensor/borg/{key}/config"
        payload = {**payload_unique[key], **payload_shared}
        payload["object_id"] = f"borg_{key}"
        payload["unique_id"] = f"borg_{key}"
        payload["state_topic"] = f"borg/{key}/state"

        # Send up configuration
        client.publish(topic, json.dumps(payload), retain=True)
        # Turn off
        client.publish(payload["state_topic"], "OFF", retain=True)

    ######## CONFIG FOR REPOSITORY INFORMATION #############
    repos = None  # get_repo_info()

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
    for i, r in enumerate(repos):
        state_topic = f"borg/repo_{i}/state"
        device = {
            "identifiers": [r["id"]],
            "name": f"Borg Repository {i}",
            "model": "Borgmatic",
            "manufacturer": "Borg",
        }
        payload_shared = {"state_topic": state_topic, "device": device}
        for key in r.keys():
            topic = f"homeassistant/sensor/borg_{i}/{key}/config"
            payload = {**payload_unique[key], **payload_shared}
            payload["object_id"] = f"borg_{i}_{key}"
            payload["unique_id"] = f"borg_{i}_{key}"
            payload["value_template"] = f"{{{{value_json.{key}}}}}"

            client.publish(topic, json.dumps(payload), retain=True)

        client.publish(state_topic, json.dumps(r), retain=True)
