# SPDX-FileCopyrightText: 2024-2025 Andrew Gunnerson
# SPDX-License-Identifier: GPL-3.0-only

import logging
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import override

from lib import modules, dependencies
from lib.filesystem import CpioFs, ExtFs
from lib.initscript import InitScript
from lib.modules import Module, ModuleRequirements

logger = logging.getLogger(__name__)


class BCRModule(Module):
    @override
    @staticmethod
    def create_custom(module: Path) -> Module:
        return BCRModule(module)

    @override
    @staticmethod
    def create_download(modules_dir: Path) -> Module:
        return BCRModule(dependencies.download_bcr(modules_dir))

    def __init__(self, module: Path) -> None:
        super().__init__()

        self.zip: Path = module

    @override
    @staticmethod
    def requirements() -> ModuleRequirements:
        return ModuleRequirements(
            boot_images=set(),
            ext_images={'system'},
            selinux_patching=False,
        )

    @override
    def inject(
        self,
        boot_fs: dict[str, CpioFs],
        ext_fs: dict[str, ExtFs],
        sepolicies: Iterable[Path],
    ) -> None:
        logger.info(f'Injecting BCR: {self.zip}')

        system_fs = ext_fs['system']
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
