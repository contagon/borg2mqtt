import json

from .utils import connect_mqtt_client, get_repo_info


def update_info():
    """Update all repository information"""
    repos = get_repo_info()

    client = connect_mqtt_client()
    for i, r in enumerate(repos):
        state_topic = f"borg/repo_{i}/state"
        client.publish(state_topic, json.dumps(r), retain=True)
