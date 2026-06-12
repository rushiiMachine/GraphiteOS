# SPDX-FileCopyrightText: 2024-2026 Andrew Gunnerson
# SPDX-License-Identifier: GPL-3.0-only
import argparse
import logging
import os
import shutil
import tempfile
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import override

from lib import modules, dependencies
from lib.external import BINARIES_DIR
from lib.filesystem import CpioFs, ExtFs
from lib.linux import linux_android_abi, linux_run
from lib.modules import Module, ModuleRequirements

logger = logging.getLogger(__name__)


class CustotaModule(Module):
    def __init__(self, module: Path) -> None:
        super().__init__()

        self.zip: Path = module
        self.abi: str = linux_android_abi()

    @override
    @staticmethod
    def create(args: argparse.Namespace) -> CustotaModule | None:
        value: Path | bool | None = args.module_custota

        if value:
            return CustotaModule(dependencies.download_custota(BINARIES_DIR))
        elif isinstance(value, Path):
            if not value.is_file():
                raise ValueError('CustotaModule module path does not exist!')
            return CustotaModule(value)
        else:
            return None

    @override
    @staticmethod
    def register_args(parser: argparse._ActionsContainer):
        parser.add_argument(
            '--module-custota',
            help='Apply module that installs custom OTA updater app.',
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
        logger.info(f'Injecting Custota: {self.zip}')

        system_fs = ext_fs['system']

        with zipfile.ZipFile(self.zip, 'r') as z:
            for path in z.namelist():
                if not path.endswith('.apk') and not path.endswith('.xml'):
                    continue

                modules.zip_extract(z, path, system_fs)

            # Add SELinux rules.
            with tempfile.NamedTemporaryFile(delete_on_close=False) as f_temp:
                with z.open(f'custota-selinux.{self.abi}') as f_exe:
                    shutil.copyfileobj(f_exe, f_temp)
                os.fchmod(f_temp.fileno(), 0o700)
                f_temp.close()

                for sepolicy in sepolicies:
                    logger.info(f'Adding Custota SELinux rules: {sepolicy}')

                    linux_run(
                        [
                            f_temp.name,
                            '--source', sepolicy,
                            '--target', sepolicy,
                        ],
                        inputs=[f_temp.name, sepolicy],
                        outputs=[sepolicy],
                    )

            seapp = 'system/etc/selinux/plat_seapp_contexts'
            logger.info(f'Adding Custota seapp context: {seapp}')

            with (
                z.open('plat_seapp_contexts', 'r') as f_in,
                system_fs.open(seapp, 'ab') as f_out,
            ):
                shutil.copyfileobj(f_in, f_out)
                f_out.write(b'\n')
