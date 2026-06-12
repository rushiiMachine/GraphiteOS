import argparse
import logging
import shutil
from collections.abc import Iterable
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import override

from lib.filesystem import CpioFs, ExtFs
from lib.modules import Module, ModuleRequirements

logger = logging.getLogger(__name__)

# The path inside the `product` partition, mounted as /product/ and /system/product/
# https://github.com/GrapheneOS/platform_frameworks_base/blob/0f64a40c7ae7caa0ef7cd6a1b11f2f3f0ff02146/cmds/bootanimation/BootAnimation.cpp#L719-L733
BOOTANIMATION_PATH = '/media/bootanimation.zip'
BOOTANIMATION_DARK_PATH = '/media/bootanimation-dark.zip'

# This has to be explicitly specified since product partition is mounted at /product/ and
# thus matching sepolicies by path doesn't work.
# https://github.com/GrapheneOS/platform_system_sepolicy/blob/1fb906c0b5663edc137064a183d56cb9a075407f/private/file_contexts#L509
BOOTANIMATION_SELINUX = 'u:object_r:system_file:s0'


class BootAnimationModule(Module):
    def __init__(
        self,
        bootanimation: Path | Traversable,
        bootanimation_dark: Path | Traversable | None = None
    ) -> None:
        super().__init__()

        self.bootanimation: Path | Traversable = bootanimation
        self.bootanimation_dark: Path | Traversable | None = bootanimation_dark

    @override
    @staticmethod
    def create(args: argparse.Namespace) -> BootAnimationModule | None:
        value: Path | bool | None = args.module_bootanimation

        if value:
            assets = resources.files(__package__) / '..' / 'assets'
            bootanimation = assets / 'bootanimation.zip'
            bootanimation_dark = assets / 'bootanimation-dark.zip'

            return BootAnimationModule(bootanimation, bootanimation_dark)
        elif isinstance(value, Path):
            if not value.is_file():
                raise ValueError('BootAnimationModule module path does not exist!')

            return BootAnimationModule(value)
        else:
            return None

    @override
    @staticmethod
    def register_args(parser: argparse._ActionsContainer):
        parser.add_argument(
            '--module-bootanimation',
            help='Replaces or adds stock Pixel boot animations to the system image.\n'
                 'Specifying a custom bootanimation.zip will inject that instead.',
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
            ext_images={'product'},
            selinux_patching=False,
        )

    @override
    def inject(
        self,
        boot_fs: dict[str, CpioFs],
        ext_fs: dict[str, ExtFs],
        sepolicies: Iterable[Path],
    ) -> None:
        product_fs = ext_fs['product']

        def patch_bootanimation(path: str, new: Path | Traversable):
            with new.open('rb') as src:
                with product_fs.open(path, 'wb',
                                     label=BOOTANIMATION_SELINUX) as dst:
                    shutil.copyfileobj(src, dst)

        logger.info(f'Replacing boot animation')
        patch_bootanimation(BOOTANIMATION_PATH, self.bootanimation)

        if self.bootanimation_dark is not None:
            logger.info(f'Replacing dark boot animation')
            patch_bootanimation(BOOTANIMATION_DARK_PATH, self.bootanimation_dark)
