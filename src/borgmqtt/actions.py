from .repo import MQTTSettings, Repository


def parse(args) -> tuple[list[Repository], MQTTSettings]:
    return [Repository()], MQTTSettings


def generate(repos: list[Repository], mqtt: MQTTSettings):
    print("generate")


def setup(repos: list[Repository], mqtt: MQTTSettings):
    print("setup")


def update(repos: list[Repository], mqtt: MQTTSettings):
    print("update")
