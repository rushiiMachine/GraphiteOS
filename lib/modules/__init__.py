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
    def create_custom(module: Path) -> Module:
        ...

    @staticmethod
    @abstractmethod
    def create_download(modules_dir: Path) -> Module:
        ...

    @staticmethod
    @abstractmethod
    def requirements() -> ModuleRequirements:
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
    from lib.modules.alterinstaller import AlterInstallerModule
    from lib.modules.bcr import BCRModule
    from lib.modules.custota import CustotaModule
    from lib.modules.msd import MSDModule
    from lib.modules.oemunlockonboot import OEMUnlockOnBootModule

    return {
        'alterinstaller': AlterInstallerModule,
        'bcr': BCRModule,
        'custota': CustotaModule,
        'msd': MSDModule,
        'oemunlockonboot': OEMUnlockOnBootModule,
    }


def create_modules(modules_dir: Path, args: argparse.Namespace) -> dict[str, Module]:
    def create(name: str, module: type[Module]) -> tuple[str, Module] | None:
        module_path: Path | None = getattr(args, f'module_{name}')

        if module_path is None:
            return None
        elif isinstance(module_path, Path):
            if not module_path.is_file():
                logger.error(f'Module {name} at {module_path} does not exist!')
                exit(1)
            else:
                return name, module.create_custom(module_path)
        else:
            return name, module.create_download(modules_dir)

    modules = [create(name, module) for name, module in all_modules().items()]
    return dict(filter(lambda x: x is not None, modules))


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
