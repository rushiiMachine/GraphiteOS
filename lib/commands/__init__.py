import argparse
from argparse import Namespace

from lib.commands.encode_keys import args_encode_keys
from lib.commands.keys import args_keys
from lib.commands.patch import args_patch


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(dest='command', required=True)

    args_patch(subparsers)
    args_keys(subparsers)
    args_encode_keys(subparsers)

    return parser.parse_args()
