# SPDX-FileCopyrightText: 2024-2025 Andrew Gunnerson
# SPDX-License-Identifier: GPL-3.0-only

import argparse
import logging
import zipfile
from pathlib import Path
from typing import override

from lib import modules, dependencies
from lib.external import BINARIES_DIR
from lib.initscript import InitScript
from lib.modules import Module, ModuleContext, ModuleRequirements

logger = logging.getLogger(__name__)


class AlterInstallerModule(Module):
    def __init__(self, module: Path) -> None:
        super().__init__()

        self.zip: Path = module

    @override
    @staticmethod
    def create(args: argparse.Namespace) -> AlterInstallerModule | None:
        value: Path | bool | None = args.module_alterinstaller

        if value:
            return AlterInstallerModule(dependencies.download_alterinstaller(BINARIES_DIR))
        elif isinstance(value, Path):
            if not value.is_file():
                raise ValueError('AlterInstaller module path does not exist!')
            return AlterInstallerModule(value)
        else:
            return None

    @override
    @staticmethod
    def register_args(parser: argparse._ActionsContainer):
        parser.add_argument(
            '--module-alterinstaller',
            help='Apply module that spoofs Android PackageManager Installer fields.',
            metavar='<ZIP>',
            type=Path,
            nargs='?',
            const=True,
            default=None,
        )

    @override
    @staticmethod
    def requirements() -> ModuleRequirements:
        return ModuleRequirements(
            ext_images={'system'},
        )

    @override
    def inject(self, context: ModuleContext) -> None:
        logger.info(f'Injecting AlterInstaller: {self.zip}')

        system_fs = context.ext_fs['system']

        with zipfile.ZipFile(self.zip, 'r') as z:
            apk = next(n for n in z.namelist() if n.endswith('.apk'))
            # Intentionally put it somewhere that will not be picked up by
            # Android's package manager since it's not really an app and the apk
            # is unsigned.
            path = 'system/bin/alterinstaller.apk'

            modules.zip_extract(z, apk, system_fs, output=path)

        InitScript(
            name='alterinstaller_backup',
            command=[
                '/system/bin/cp',
                '/data/system/packages.xml',
                '/data/local/tmp/AlterInstaller.backup.xml',
            ],
            class_='main',
            user='system',
            # For writing to /data/local/tmp/.
            group='shell',
            seclabel='u:r:su:s0',
            # This must run and exit before the package manager starts.
            condition='post-fs-data',
            blocking=True,
        ).add_to(system_fs)

        InitScript(
            name='alterinstaller_exec',
            command=[
                '/system/bin/app_process',
                '/',
                'com.chiller3.alterinstaller.Main',
                'apply',
                '/data/local/tmp/AlterInstaller.json',
                '/data/system/packages.xml',
                '/data/system/packages.xml',
            ],
            class_='main',
            user='system',
            group='system',
            seclabel='u:r:su:s0',
            env={
                'CLASSPATH': f'/{path}',
            },
            # This must run and exit before the package manager starts.
            condition='post-fs-data',
            blocking=True,
        ).add_to(system_fs)
