import yaml

from .repo import MQTTSettings, Repository


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

    repos = [Repository(**i) for i in config["repos"]]

    if args.operation == "update" and args.name is not None:
        repos = [r for r in repos if r.name == args.name]
        if len(repos) == 0:
            raise ValueError("This repo name was not found!")

    return repos, mqtt


def generate(repos: list[Repository], mqtt: MQTTSettings):
    print("generate")


def setup(repos: list[Repository], mqtt: MQTTSettings):
    for r in repos:
        r.setup(mqtt)


def update(repos: list[Repository], mqtt: MQTTSettings):
    for r in repos:
        r.update(mqtt)
