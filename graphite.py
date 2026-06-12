#!/usr/bin/env -S uv run --script

# SPDX-FileCopyrightText: 2024-2025 Andrew Gunnerson
# SPDX-License-Identifier: GPL-3.0-only

import logging
import os
import subprocess
import tempfile
from pathlib import Path

from lib import commands, dependencies, external

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.DEBUG,  # TODO: support DEBUG env var
        format='\x1b[1m[%(levelname)s] %(message)s\x1b[0m',
    )

    # Parse and validate args
    args = commands.parse_args()

    # Download tool binaries
    dependencies.download_avbroot(external.BINARIES_DIR)
    dependencies.download_afsr(external.BINARIES_DIR)
    dependencies.download_custota_tool(external.BINARIES_DIR)

    # Add binaries dir to path
    os.environ['PATH'] = str(external.BINARIES_DIR) + ':' + os.environ['PATH']

    # Run subcommand
    failure = False
    try:
        actions = commands.all_command_actions()

        with tempfile.TemporaryDirectory() as temp_dir:
            actions[args.command](args, Path(temp_dir))
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
