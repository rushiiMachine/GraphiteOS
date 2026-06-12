import argparse
from argparse import Namespace
from pathlib import Path
from typing import Callable

from lib import graphite_version, dependencies
from lib.commands import encode_keys, generate_keys, patch, server


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser(
        prog='graphite',
        description='GraphiteOS: rushii\'s rooted & modded OTA patching tool targeting GrapheneOS',
        formatter_class=argparse.RawTextHelpFormatter,
        allow_abbrev=False,
        suggest_on_error=True,
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {graphite_version()}\n\n'
                f'avbroot {dependencies.AVBROOT_VERSION}\n'
                f'afsr {dependencies.AFSR_VERSION}\n'
                f'custota {dependencies.CUSTOTA_VERSION}\n'
                f'AlterInstaller {dependencies.ALTERINSTALLER_VERSION}\n'
                f'BCR {dependencies.BCR_VERSION}\n'
                f'MSD {dependencies.MSD_VERSION}\n'
                f'Magisk v{dependencies.MAGISK_VERSION}\n'
                f'Magisk (pixincreate) {dependencies.MAGISK_PIXINCREATE_VERSION}',
    )
    parser.add_argument(
        '--debug-shell',
        action='store_true',
        help='Spawn a debug shell before cleaning up the temporary directory.',
    )
    subparsers = parser.add_subparsers(
        title='commands',
        dest='command',
        metavar='<COMMAND>',
        required=True,
    )

    encode_keys.register(subparsers)
    generate_keys.register(subparsers)
    patch.register(subparsers)
    server.register(subparsers)

    return parser.parse_args()


def all_command_actions() -> dict[str, Callable[[argparse.Namespace, Path], None]]:
    return {
        'generate-keys': generate_keys.run,
        'encode-keys': encode_keys.run,
        'patch': patch.run,
        'server': server.run,
    }
