import argparse
from argparse import Namespace

from lib.commands.keys import args_keys
from lib.commands.patch import args_patch


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    args_patch(subparsers)
    args_keys(subparsers)

    return parser.parse_args()
