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


class BCRModule(Module):
    def __init__(self, module: Path) -> None:
        super().__init__()

        self.zip: Path = module

    @override
    @staticmethod
    def create(args: argparse.Namespace) -> BCRModule | None:
        value: Path | bool | None = args.module_bcr

        if value:
            return BCRModule(dependencies.download_bcr(BINARIES_DIR))
        elif isinstance(value, Path):
            if not value.is_file():
                raise ValueError('BCRModule module path does not exist!')
            return BCRModule(value)
        else:
            return None

    @override
    @staticmethod
    def register_args(parser: argparse._ActionsContainer):
        parser.add_argument(
            '--module-bcr',
            help='Apply module that installs Basic Call Recorder.',
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
        logger.info(f'Injecting BCR: {self.zip}')

        system_fs = context.ext_fs['system']
        apk = None

        with zipfile.ZipFile(self.zip, 'r') as z:
            for path in z.namelist():
                if not path.endswith('.apk') and not path.endswith('.xml'):
                    continue
                elif path.endswith('.apk'):
                    apk = path

                modules.zip_extract(z, path, system_fs)

        assert apk

        InitScript(
            name='bcr_remove_hard_restrictions',
            command=[
                '/system/bin/app_process',
                '/',
                'com.chiller3.bcr.standalone.RemoveHardRestrictionsKt',
            ],
            class_='main',
            user='system',
            group='system',
            seclabel='u:r:su:s0',
            env={
                'CLASSPATH': f'/{apk}',
            },
        ).add_to(system_fs)
