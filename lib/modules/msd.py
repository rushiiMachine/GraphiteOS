# SPDX-FileCopyrightText: 2024-2026 Andrew Gunnerson
# SPDX-License-Identifier: GPL-3.0-only

import logging
import os
import shutil
import tempfile
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import override

from lib import modules, dependencies
from lib.filesystem import CpioFs, ExtFs
from lib.initscript import InitScript
from lib.linux import linux_android_abi, linux_run
from lib.modules import Module, ModuleRequirements

logger = logging.getLogger(__name__)


class MSDModule(Module):
    @override
    @staticmethod
    def create_custom(module: Path) -> Module:
        return MSDModule(module)

    @override
    @staticmethod
    def create_download(modules_dir: Path) -> Module:
        return MSDModule(dependencies.download_msd(modules_dir))

    def __init__(self, module: Path) -> None:
        super().__init__()

        self.zip: Path = module
        self.abi: str = linux_android_abi()

    @override
    @staticmethod
    def requirements() -> ModuleRequirements:
        return ModuleRequirements(
            boot_images=set(),
            ext_images={'system'},
            selinux_patching=True,
        )

    @override
    def inject(
        self,
        boot_fs: dict[str, CpioFs],
        ext_fs: dict[str, ExtFs],
        sepolicies: Iterable[Path],
    ) -> None:
        logger.info(f'Injecting MSD: {self.zip}')

        system_fs = ext_fs['system']

        with zipfile.ZipFile(self.zip, 'r') as z:
            for path in z.namelist():
                if path == 'msd-tool.arm64-v8a':
                    dest_path = 'system/bin/msd-tool'
                    perms = 0o755
                elif path.endswith('.apk'):
                    dest_path = path
                    perms = 0o644
                else:
                    continue

                modules.zip_extract(z, path, system_fs, mode=perms, output=dest_path)

            # Add SELinux rules.
            with tempfile.NamedTemporaryFile(delete_on_close=False) as f_temp:
                with z.open(f'msd-tool.{self.abi}') as f_exe:
                    shutil.copyfileobj(f_exe, f_temp)
                os.fchmod(f_temp.fileno(), 0o700)
                f_temp.close()

                for sepolicy in sepolicies:
                    logger.info(f'Adding MSD SELinux rules: {sepolicy}')

                    linux_run(
                        [
                            f_temp.name,
                            'sepatch',
                            '--source', sepolicy,
                            '--target', sepolicy,
                        ],
                        inputs=[f_temp.name, sepolicy],
                        outputs=[sepolicy],
                    )

            seapp = 'system/etc/selinux/plat_seapp_contexts'
            logger.info(f'Adding MSD seapp context: {seapp}')

            with (
                z.open('plat_seapp_contexts', 'r') as f_in,
                system_fs.open(seapp, 'ab') as f_out,
            ):
                shutil.copyfileobj(f_in, f_out)
                f_out.write(b'\n')

        InitScript(
            name='msd_daemon',
            command=[
                '/system/bin/msd-tool',
                'daemon',
                '--log-target', 'logcat',
                '--log-level', 'debug',
            ],
            class_='main',
            user='system',
            group='system',
            seclabel='u:r:msd_daemon:s0',
            capabilities=['CHOWN'],
        ).add_to(system_fs)
