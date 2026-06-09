#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024-2025 Andrew Gunnerson
# SPDX-License-Identifier: GPL-3.0-only

import logging
import os
import subprocess
import tempfile
from pathlib import Path

from lib import commands, dependencies
from lib.commands.encode_keys import command_encode_keys
from lib.commands.keys import command_keys
from lib.commands.patch import command_patch

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.DEBUG,  # TODO: support DEBUG env var
        format='\x1b[1m[%(levelname)s] %(message)s\x1b[0m',
    )

    args = commands.parse_args()
    binaries_dir = Path(os.getcwd()) / '.bin'

    # Download tool binaries
    dependencies.download_avbroot(binaries_dir)
    if args.command == 'patch':
        dependencies.download_afsr(binaries_dir)

        if getattr(args, 'generate_custota', False):
            dependencies.download_custota_tool(binaries_dir)

    # Add binaries dir to path
    os.environ['PATH'] = str(binaries_dir) + ':' + os.environ['PATH']

    failure = False
    try:
        if args.command == 'patch':
            with tempfile.TemporaryDirectory() as temp_dir:
                command_patch(args, Path(temp_dir), binaries_dir)
        elif args.command == 'keys':
            command_keys(args)
        elif args.command == 'encode-keys':
            command_encode_keys(args)
    except Exception as e:
        failure = True
        logging.error(f'Failed to run {args.command} command!', exc_info=e)

    if getattr(args, 'debug_shell', False):
        shell = os.getenv('SHELL', 'bash')
        logger.info(f'Debug shell: {shell}')
        subprocess.run([shell], cwd=temp_dir)

    exit(1 if failure else 0)


if __name__ == '__main__':
    main()
