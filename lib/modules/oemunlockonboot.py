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


class OEMUnlockOnBootModule(Module):
    def __init__(self, module: Path) -> None:
        super().__init__()

        self.zip: Path = module

    @override
    @staticmethod
    def create(args: argparse.Namespace) -> OEMUnlockOnBootModule | None:
        value: Path | bool | None = args.module_oemunlockonboot

        if value:
            return OEMUnlockOnBootModule(dependencies.download_bcr(BINARIES_DIR))
        elif isinstance(value, Path):
            if not value.is_file():
                raise ValueError('OEMUnlockOnBootModule module path does not exist!')
            return OEMUnlockOnBootModule(value)
        else:
            return None

    @override
    @staticmethod
    def register_args(parser: argparse._ActionsContainer):
        parser.add_argument(
            '--module-oemunlockonboot',
            help='Apply module to always enable Android\'s `OEM unlocking` toggle on every boot.\n'
                 'Using this module is HIGHLY recommended to prevent accidental hard-bricking.',
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
        logger.info(f'Injecting OEMUnlockOnBoot: {self.zip}')

        system_fs = context.ext_fs['system']

        with zipfile.ZipFile(self.zip, 'r') as z:
            apk = next(n for n in z.namelist() if n.endswith('.apk'))
            # Intentionally put it somewhere that won't be picked up by
            # Android's package manager since it's not really an app and the apk
            # is unsigned.
            path = 'system/bin/oemunlockonboot.apk'

            modules.zip_extract(z, apk, system_fs, output=path)

        InitScript(
            name='oemunlockonboot',
            command=[
                '/system/bin/app_process',
                '/',
                'com.chiller3.oemunlockonboot.Main',
            ],
            class_='main',
            user='system',
            group='system',
            seclabel='u:r:su:s0',
            env={
                'CLASSPATH': f'/{path}',
            },
        ).add_to(system_fs)
