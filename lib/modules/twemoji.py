import logging
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import override

import requests

from lib.filesystem import CpioFs, ExtFs
from lib.modules import Module, ModuleRequirements

logger = logging.getLogger(__name__)

TWEMOJI_TTF_VERSION = '17.0.2'
TWEMOJI_TTF_URL = \
    f'https://github.com/JoeBlakeB/ttf-twemoji/releases/download/{TWEMOJI_TTF_VERSION}/Twemoji-{TWEMOJI_TTF_VERSION}.ttf'

TARGET_FONT_PATH = '/system/fonts/NotoColorEmoji.ttf'


class TwemojiModule(Module):
    @override
    @staticmethod
    def create_custom(module: Path) -> Module:
        return TwemojiModule(module)

    @override
    @staticmethod
    def create_download(modules_dir: Path) -> Module:
        font_file = modules_dir / f'twemoji-{TWEMOJI_TTF_VERSION}.ttf'

        if not font_file.is_file():
            with requests.get(TWEMOJI_TTF_URL, stream=True) as resp:
                resp.raise_for_status()
                with font_file.open('wb') as file:
                    shutil.copyfileobj(resp.raw, file)

        return TwemojiModule(font_file)

    def __init__(self, font: Path) -> None:
        super().__init__()

        self.font: Path = font

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
        logger.info(f'Injecting Twemoji: {self.font} to {TARGET_FONT_PATH}')

        system_fs = ext_fs['system']

        with (
            system_fs.open(TARGET_FONT_PATH, 'wb') as dst,
            self.font.open('rb') as src
        ):
            shutil.copyfileobj(src, dst)
