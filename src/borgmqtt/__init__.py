import argparse
import os

from platformdirs import user_config_dir

from .const import APP_NAME


def run_borgmqtt():
    parser = argparse.ArgumentParser(
        prog="borgmqtt",
        description="Send borg repository settings over mqtt",
    )
    parser.add_argument("operation", choices=["setup", "update", "generate"])
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        type=str,
        help="Path to a configuration file. \
                Defaults to $HOME/.config/borgmqtt/config.yaml otherwise.",
    )
    parser.add_argument(
        "-n",
        "--name",
        default=None,
        type=str,
        help="Name of repo in configuration files. \
                 Default runs all of them.",
    )

    args = parser.parse_args()

    # TODO: Parse config
    if args.config is None:
        # TODO: Search for config here
        args.config = os.path.join(user_config_dir(APP_NAME), "config.yml")

    if args.operation == "setup":
        pass
    elif args.operation == "update":
        pass
    elif args.operation == "gen_config":
        pass


if __name__ == "__main__":
    run_borgmqtt()
