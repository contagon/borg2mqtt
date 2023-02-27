import os

import yaml

from .const import APP_NAME
from .repo import MQTTSettings, Repository

EXAMPLE_CONFIG = """
# ---------------- Sample configuration file ---------------- #
# These are the default MQTT values - none are required
mqtt:
  host: localhost
  port: 1883
  user: ""
  password: ""

# Put in as many repositories as desired
repos:
    # Required
  - repo: user@address:/path/to/backup
    # Optional, defaults to the same as repo if not specified
    # This will be used to make entity_ids in HA
    name: Local Data
    # Optional
    key: ""
    # Optional, choose one of kB, MB, GB, TB. Defaults to GB.
    units: GB
"""


def parse(args) -> tuple[list[Repository], MQTTSettings]:
    with open(args.config) as f:
        config = yaml.safe_load(f)

    # It's valid to have no mqtt config
    if "mqtt" not in config:
        config["mqtt"] = {}

    # But not no repos
    if "repos" not in config:
        raise ValueError("Configuration didn't have any repos.")

    mqtt = MQTTSettings(**config["mqtt"])

    repos = [Repository(verbose=args.verbose, **i) for i in config["repos"]]

    if args.operation == "update" and args.name is not None:
        repos = [r for r in repos if r.name == args.name]
        if len(repos) == 0:
            raise ValueError("This repo name was not found!")

    return repos, mqtt


def generate(path: str):
    # Make sure we're not overriding anything
    if os.path.exists(path):
        raise ValueError(
            f"A file exists at {path} already, remove it to make a new one"
        )

    # Make directory to put config file in
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Save example config
    print(f"[{APP_NAME}] Making config file at {path}")
    with open(path, "w") as f:
        f.write(EXAMPLE_CONFIG)


def setup(repos: list[Repository], mqtt: MQTTSettings):
    for r in repos:
        r.setup(mqtt)


def update(repos: list[Repository], mqtt: MQTTSettings):
    for r in repos:
        r.update(mqtt)
