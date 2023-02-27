import argparse
import os

from platformdirs import user_config_dir

from . import actions
from .const import APP_NAME


def run_borg2mqtt():
    parser = argparse.ArgumentParser(
        prog="borg2mqtt",
        description="Send borg repository settings over mqtt",
    )
    default_path = os.path.join(user_config_dir(APP_NAME), "config.yml")
    parser.add_argument(
        "-c",
        "--config",
        default=default_path,
        type=str,
        help="Path to load/save a configuration file. \
                Defaults to $HOME/.config/borg2mqtt/config.yml.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        help="Verbose output. Repeat 1-3 times for varying levels.",
    )

    subparsers = parser.add_subparsers(
        help="Type of operation to perform", dest="operation"
    )

    # ------------------------- Generate configuration file ------------------------- #
    subparsers.add_parser(
        "generate",
        help="Generate sample config file, or make config file from borgmatic config.",
    )

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

    if args.operation == "generate":
        actions.generate(args.config)
    else:
        repos, mqtt = actions.parse(args)
        args.func(repos, mqtt)


if __name__ == "__main__":
    run_borg2mqtt()
