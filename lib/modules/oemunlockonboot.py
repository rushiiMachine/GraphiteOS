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


class OEMUnlockOnBootModule(Module):
    @override
    @staticmethod
    def create_custom(module: Path) -> Module:
        return OEMUnlockOnBootModule(module)

    @override
    @staticmethod
    def create_download(modules_dir: Path) -> Module:
        return OEMUnlockOnBootModule(dependencies.download_oemunlockonboot(modules_dir))

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
        logger.info(f'Injecting OEMUnlockOnBoot: {self.zip}')

        system_fs = ext_fs['system']

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
