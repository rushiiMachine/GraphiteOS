import argparse
import dataclasses
import logging
import zipfile
from pathlib import Path

import tomlkit

from lib import external, filesystem, modules
from lib.commands.common import register_keys_args
from lib.dependencies import download_magisk, download_magisk_pixincreate
from lib.external import BINARIES_DIR, KeyFile, InputFile
from lib.filesystem import CpioFs, CpioInfo, ExtFs, ExtInfo

logger = logging.getLogger(__name__)


def register(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        'patch',
        help='Patch and resign an OTA',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        allow_abbrev=False,
        suggest_on_error=True,
    )
    parser.set_defaults()

    group_input = parser.add_argument_group(
        title='Input',
        description='Input OTA options',
    )
    group_input.add_argument(
        '-i',
        '--input',
        help='Input OTA zip',
        metavar='<FILE>',
        type=Path,
        required=True,
    )
    group_input.add_argument(
        '--verify-public-key-avb',
        help='AVB public key file for verifying input OTA (optional)',
        metavar='<original_avb_pkmd.bin>',
        type=Path,
    )
    group_input.add_argument(
        '--verify-cert-ota',
        help='OTA certificate file for verifying input OTA (optional)',
        metavar='<original_ota.crt>',
        type=Path,
    )

    group_output = parser.add_argument_group(
        title='Output',
        description='Patched OTA output options',
    )
    group_output.add_argument(
        '--output',
        help='Output OTA zip. Defaults to input + ".patched"',
        metavar='<FILE>',
        type=Path,
    )
    group_output.add_argument(
        '--generate-custota',
        help='Generate a Custota csig and manifest json',
        action='store_true',
    )

    register_keys_args(parser)

    group_root = parser.add_argument_group(
        title='Root',
        description='Magisk patching options.'
    )
    group_root.add_argument(
        '--magisk',
        help='Applies Magisk boot patches. This accepts either a path to a Magisk APK, '
             '"topjohnwu", "pixincreate", or if none specified, defaults to original Magisk (topjohnwu).',
        metavar='<APK>',
        type=str,
        nargs='?',
        const='topjohnwu',
        default=None,
    )
    group_root.add_argument(
        '--magisk-preinit-device',
        help='Magisk preinit block device (version >=25211 only)',
        metavar='<PARTITION>',
        type=str,
    )

    group_modules = parser.add_argument_group(
        title='Modules',
        description='Custom modules to be applied directly to the OTA.'
    )
    for module in modules.all_modules().values():
        module.register_args(group_modules)

    group_misc = parser.add_argument_group(
        title='Miscellaneous',
        description='Other niche configuration options',
    )
    group_misc.add_argument(
        '--patch-arg',
        help='Extra arguments to pass to `avbroot ota patch`',
        metavar='<ARGS...>',
        action='append',
        default=['--rootless'],
    )


def run(args: argparse.Namespace, temp_dir: Path):
    logger.info("Patching OTA...")

    signing_key_avb = KeyFile(
        input_env=args.signing_key_avb_env,
        input_file=args.signing_key_avb,
        pass_env=args.signing_key_avb_password_env,
        pass_file=args.signing_key_avb_password_file,
    )
    signing_key_ota = KeyFile(
        input_env=args.signing_key_ota_env,
        input_file=args.signing_key_ota,
        pass_env=args.signing_key_ota_password_env,
        pass_file=args.signing_key_ota_password_file,
    )
    signing_cert_ota = InputFile(
        input_env=args.signing_cert_ota_env,
        input_file=args.signing_cert_ota,
    )

    # Set advanced args defaults

    if args.output is None:
        args.output = Path(f'{args.input}.patched')

    match args.magisk:
        case None:
            magisk = None
        case 'topjohnwu':
            logger.info('Will be injecting original Magisk')
            magisk = download_magisk(BINARIES_DIR)
        case 'pixincreate':
            logger.info('Will be injecting Magisk fork pixincreate for GrapheneOS')
            magisk = download_magisk_pixincreate(BINARIES_DIR)
        case _:
            if not Path(args.magisk).is_file():
                raise Exception(f'Specified Magisk APK file does not exist: {args.magisk}')
            else:
                magisk = Path(args.magisk)
                logger.info(f'Will be injecting custom Magisk: {args.magisk}')

    if magisk is not None:
        if '--rootless' in args.patch_arg:
            args.patch_arg.remove('--rootless')

        if args.magisk_preinit_device is None:
            logger.fatal(f'Injecting Magisk requires a --magisk-preinit-device to be specified!')
            exit(1)

        args.patch_arg += [
            '--magisk', magisk,
            '--magisk-preinit-device', args.magisk_preinit_device,
        ]

    inject_modules: list[modules.Module] = []
    need_boot_fs: set[str] = set()
    need_ext_fs: set[str] = set()
    need_sepolicies = False

    # Get OTA partitions
    partitions = external.list_ota(args.input)

    # Non GKI-2.0 devices such as the Pixel 4a contain sepolicies on boot partition
    sepolicies_partition = 'vendor_boot' if ('vendor_boot' in partitions) else 'boot'

    for name, module_type in modules.all_modules().items():
        module = module_type.create(args)
        if module is None:
            continue

        inject_modules.append(module)

        requirements = module.requirements()
        need_boot_fs |= requirements.boot_images
        need_ext_fs |= requirements.ext_images
        need_sepolicies |= requirements.selinux_patching

    logger.info('Will be injecting modules: ' +
                ", ".join(type(m).__name__ for m in inject_modules))

    # If we're messing with any ext filesystems, then we need to load the system
    # images to get the list of SELinux contexts.
    if need_ext_fs:
        need_ext_fs.add('system')

    # If we're patching the SELinux policy, then we need to patch both copies of
    # the precompiled policy.
    if need_sepolicies:
        need_boot_fs.add(sepolicies_partition)
        need_ext_fs.add('vendor')

    # Verify OTA.
    external.verify_ota(args.input, args.verify_public_key_avb, args.verify_cert_ota)

    # Unpack OTA.
    images_dir = temp_dir / 'images'
    if need_boot_fs or need_ext_fs:
        external.unpack_ota(args.input, images_dir, need_boot_fs | need_ext_fs)

    # Unpack boot images.
    boot_fs: dict[str, CpioFs] = {}
    for name in need_boot_fs:
        paths = BootImagePaths(images_dir, temp_dir, name)

        paths.unpacked.mkdir()
        external.unpack_avb(paths.image, paths.unpacked)
        external.unpack_boot(paths.raw_image, paths.unpacked)
        external.unpack_cpio(paths.ramdisk, paths.unpacked)

        with open(paths.metadata, 'rb') as f:
            info = CpioInfo.model_validate(tomlkit.load(f))

        boot_fs[name] = CpioFs(info=info, tree=paths.tree)

    # Unpack ext filesystem images.
    ext_fs: dict[str, ExtFs] = {}
    for name in need_ext_fs:
        paths = ExtImagePaths(images_dir, temp_dir, name)

        paths.unpacked.mkdir()
        external.unpack_avb(paths.image, paths.unpacked)
        external.unpack_fs(paths.raw_image, paths.unpacked)

        with open(paths.metadata, 'rb') as f:
            info = ExtInfo.model_validate(tomlkit.load(f))

        ext_fs[name] = ExtFs(info=info, tree=paths.tree, contexts=[])

    # Parse SELinux label mappings for use when creating new entries.
    if ext_fs:
        contexts = filesystem.load_file_contexts(ext_fs['system'].tree /
                                                 'system' / 'etc' / 'selinux' / 'plat_file_contexts')

        for _, fs in ext_fs.items():
            fs.contexts = contexts

    # We only update the precompiled policies and leave the CIL policies alone.
    # Since we're starting from a (hopefully) properly built Android build, we
    # should never run into a situation where the precompiled sepolicy is out of
    # date and needs to be recompiled from the CIL files during boot.
    if need_sepolicies:
        selinux_policies = [
            boot_fs[sepolicies_partition].tree / 'sepolicy',
            ext_fs['vendor'].tree / 'etc' / 'selinux' / 'precompiled_sepolicy',
        ]
    else:
        selinux_policies = []

    # Inject modules.
    for module in inject_modules:
        module.inject(boot_fs, ext_fs, selinux_policies)

    # Repack ext filesystem images.
    for name, fs in ext_fs.items():
        paths = ExtImagePaths(images_dir, temp_dir, name)

        with open(paths.metadata, 'w') as f:
            tomlkit.dump(fs.info.model_dump(exclude_none=True), f)

        external.pack_fs(paths.raw_image, paths.unpacked)
        external.pack_avb(paths.image, paths.unpacked, signing_key_avb, True)

    # Repack boot images.
    for name, fs in boot_fs.items():
        paths = BootImagePaths(images_dir, temp_dir, name)

        with open(paths.metadata, 'w') as f:
            tomlkit.dump(fs.info.model_dump(exclude_none=True), f)

        external.pack_cpio(paths.ramdisk, paths.unpacked)
        external.pack_boot(paths.raw_image, paths.unpacked)
        external.pack_avb(paths.image, paths.unpacked, signing_key_avb, False)

    # Patch OTA.
    external.patch_ota(
        args.input,
        args.output,
        signing_key_avb,
        signing_key_ota,
        signing_cert_ota,
        {name: images_dir / f'{name}.img' for name in boot_fs | ext_fs},
        args.patch_arg,
    )

    if args.generate_custota:
        # Generate Custota csig.
        external.generate_csig(args.output, signing_key_ota, signing_cert_ota)

        # Generate Custota update-info.
        codename = _read_ota_metadata(args.output)['pre-device']
        update_info = args.output.parent / f'{codename}.json'
        external.generate_update_info(update_info, args.output.name)


def _read_ota_metadata(ota_zip: Path) -> dict[str, str]:
    props: dict[str, str] = {}

    with zipfile.ZipFile(ota_zip, 'r') as z:
        with z.open('META-INF/com/android/metadata', 'r') as f:
            for line in f:
                line = line.decode('UTF-8').strip()

                key, delim, value = line.partition('=')
                if not delim:
                    raise ValueError(f'Bad OTA metadata line: {line!r}')

                props[key] = value

    return props


@dataclasses.dataclass
class BootImagePaths:
    image: Path
    unpacked: Path
    raw_image: Path
    ramdisk: Path
    metadata: Path
    tree: Path

    def __init__(self, images_dir: Path, unpacked_dir: Path, name: str) -> None:
        self.image = images_dir / f'{name}.img'
        self.unpacked = unpacked_dir / name
        self.raw_image = self.unpacked / 'raw.img'
        self.ramdisk = self.unpacked / 'ramdisk.img.0'
        self.metadata = self.unpacked / 'cpio.toml'
        self.tree = self.unpacked / 'cpio_tree'


@dataclasses.dataclass
class ExtImagePaths:
    image: Path
    unpacked: Path
    raw_image: Path
    metadata: Path
    tree: Path

    def __init__(self, images_dir: Path, unpacked_dir: Path, name: str) -> None:
        self.image = images_dir / f'{name}.img'
        self.unpacked = unpacked_dir / name
        self.raw_image = self.unpacked / 'raw.img'
        self.metadata = self.unpacked / 'fs_metadata.toml'
        self.tree = self.unpacked / 'fs_tree'
