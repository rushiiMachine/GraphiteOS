import argparse
import logging
import shutil
from pathlib import Path
from typing import override

from lib import dependencies
from lib.external import BINARIES_DIR
from lib.modules import Module, ModuleContext, ModuleRequirements

logger = logging.getLogger(__name__)

TWEMOJI_TTF_VERSION = '17.0.2'
TWEMOJI_SHA256_HASH = '795b1c0fb2b89e9341826aa36fdee6510edcdee2ad6226e0d386130ab0ea2910'
TWEMOJI_TTF_URL = \
    f'https://github.com/JoeBlakeB/ttf-twemoji/releases/download/{TWEMOJI_TTF_VERSION}/Twemoji-{TWEMOJI_TTF_VERSION}.ttf'

TARGET_FONT_PATH = '/system/fonts/NotoColorEmoji.ttf'


class TwemojiModule(Module):
    def __init__(self, font: Path) -> None:
        super().__init__()

        self.font: Path = font

    @override
    @staticmethod
    def create(args: argparse.Namespace) -> TwemojiModule | None:
        value: Path | bool | None = args.module_twemoji

        if value:
            path = BINARIES_DIR / f'twemoji-{TWEMOJI_TTF_VERSION}.ttf'
            dependencies.download_file(path, TWEMOJI_TTF_URL, TWEMOJI_SHA256_HASH)
            return TwemojiModule(path)
        elif isinstance(value, Path):
            if not value.is_file():
                raise ValueError('TwemojiModule font path does not exist!')
            return TwemojiModule(value)
        else:
            return None

    @override
    @staticmethod
    def register_args(parser: argparse._ActionsContainer):
        parser.add_argument(
            '--module-twemoji',
            help='Replace default system emoji font with Twemoji.\n'
                 'Specifying a custom font file will inject that font instead.',
            metavar='<FONT_PATH>',
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
        logger.info(f'Injecting Twemoji: {self.font} to {TARGET_FONT_PATH}')

        system_fs = context.ext_fs['system']

        with (
            system_fs.open(TARGET_FONT_PATH, 'wb') as dst,
            self.font.open('rb') as src
        ):
            shutil.copyfileobj(src, dst)
