import argparse

from platformdirs import user_config_dir

from . import actions
from .const import APP_NAME


def run_borgmqtt():
    parser = argparse.ArgumentParser(
        prog="borgmqtt",
        description="Send borg repository settings over mqtt",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=user_config_dir(APP_NAME),
        type=str,
        help="Path to load/save a configuration file. \
                Defaults to $HOME/.config/borgmqtt/config.yml.",
    )

    subparsers = parser.add_subparsers(
        help="Type of operation to perform", dest="operation"
    )

    # ------------------------- Generate configuration file ------------------------- #
    generate = subparsers.add_parser(
        "generate",
        help="Generate sample config file, or make config file from borgmatic config.",
    )
    generate.set_defaults(func=actions.generate)
    generate.add_argument("--borgmatic", action="store_true")

    # ------------------------- Setup Device in HA ------------------------- #
    setup = subparsers.add_parser(
        "setup", help="Send autodiscovery Home Assistant MQTT messages."
    )
    setup.set_defaults(func=actions.setup)

    # ------------------------- Send MQTT sensor messages ------------------------- #
    update = subparsers.add_parser(
        "update", help="Send MQTT message with updated borg repo information."
    )
    update.set_defaults(func=actions.update)
    update.add_argument(
        "-n",
        "--name",
        default=None,
        type=str,
        help="Name of repo in configuration files. \
                 Default runs all of them.",
    )

    args = parser.parse_args()

    repos, mqtt = actions.parse(args)
    args.func(repos, mqtt)


if __name__ == "__main__":
    run_borgmqtt()
