# SPDX-FileCopyrightText: 2024-2025 Andrew Gunnerson
# SPDX-License-Identifier: GPL-3.0-only

import argparse
import dataclasses
import logging
import shutil
import zipfile
from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

from lib.filesystem import CpioFs, ExtFs

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class ModuleRequirements:
    boot_images: set[str]
    ext_images: set[str]
    selinux_patching: bool


class Module(ABC):
    @staticmethod
    @abstractmethod
    def create(args: argparse.Namespace) -> Module | None:
        """
        Creates self with the configuration from input arguments,
        otherwise returns None if this module is disabled.
        """
        ...

    @staticmethod
    @abstractmethod
    def requirements() -> ModuleRequirements:
        ...

    @staticmethod
    @abstractmethod
    def register_args(parser: argparse._ActionsContainer):
        ...

    @abstractmethod
    def inject(
        self,
        boot_fs: dict[str, CpioFs],
        ext_fs: dict[str, ExtFs],
        sepolicies: Iterable[Path],
    ) -> None:
        ...


def all_modules() -> dict[str, type[Module]]:
    from lib.modules.adbkeys import AdbKeysModule
    from lib.modules.alterinstaller import AlterInstallerModule
    from lib.modules.bcr import BCRModule
    from lib.modules.bootanimation import BootAnimationModule
    from lib.modules.custota import CustotaModule
    from lib.modules.msd import MSDModule
    from lib.modules.oemunlockonboot import OEMUnlockOnBootModule
    from lib.modules.twemoji import TwemojiModule

    return {
        'adbkeys': AdbKeysModule,
        'alterinstaller': AlterInstallerModule,
        'bcr': BCRModule,
        'bootanimation': BootAnimationModule,
        'custota': CustotaModule,
        'msd': MSDModule,
        'oemunlockonboot': OEMUnlockOnBootModule,
        'twemoji': TwemojiModule,
    }


def zip_extract(
    archive: zipfile.ZipFile,
    name: str,
    fs: ExtFs,
    mode: int = 0o644,
    parent_mode: int = 0o755,
    output: str | None = None,
):
    path = PurePosixPath(output or name)

    fs.mkdir(path.parent, mode=parent_mode, parents=True, exist_ok=True)
    with fs.open(path, 'wb', mode=mode) as f_out:
        with archive.open(name, 'r') as f_in:
            shutil.copyfileobj(f_in, f_out)
