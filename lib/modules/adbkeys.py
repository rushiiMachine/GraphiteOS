import argparse
import logging
from typing import override

from lib.modules import Module, ModuleContext, ModuleRequirements

logger = logging.getLogger(__name__)


class AdbKeysModule(Module):
    def __init__(self, keys: list[str]) -> None:
        super().__init__()

        self.keys: set[str] = set(keys)

    @override
    @staticmethod
    def create(args: argparse.Namespace) -> AdbKeysModule | None:
        keys: list[str] | None = args.module_adb_keys

        if keys is None or len(keys) == 0:
            return None

        return AdbKeysModule(keys)

    @override
    @staticmethod
    def register_args(parser: argparse._ActionsContainer):
        parser.add_argument(
            '--module-adb-keys',
            help='Append an always-trusted authorization ADB vendor key.',
            metavar='<PUBKEY>',
            nargs='+',
        )

    @override
    @staticmethod
    def requirements() -> ModuleRequirements:
        return ModuleRequirements(
            ext_images={'system'},
        )

    @override
    def inject(self, context: ModuleContext) -> None:
        logger.info('Injecting ADB keys:\n    ' + '\n    '.join(self.keys))

        system_fs = context.ext_fs['system']

        with system_fs.open("/adb_keys", 'a') as f:
            f.newlines
            f.write('\n')
            for key in self.keys:
                f.write(key)
                f.write('\n')
