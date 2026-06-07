import argparse
import dataclasses
import logging
import os
import zipfile
from pathlib import Path

import tomlkit

from lib import external, filesystem, modules
from lib.filesystem import CpioFs, CpioInfo, ExtFs, ExtInfo

logger = logging.getLogger(__name__)
default_keys_dir = Path(os.getcwd()) / '.keys'


def args_patch(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        'patch',
        help='Patches and resigns an OTA',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Input OTA zip',
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output OTA zip',
    )
    parser.add_argument(
        '--generate-custota',
        action='store_true',
        help='Generate a Custota csig and manifest json',
    )
    parser.add_argument(
        '--verify-public-key-avb',
        type=Path,
        help='AVB public key file for verifying input OTA',
    )
    parser.add_argument(
        '--verify-cert-ota',
        type=Path,
        help='OTA certificate file for verifying input OTA',
    )
    parser.add_argument(
        '--sign-key-avb',
        type=Path,
        help='AVB private key file for signing output OTA',
        default=default_keys_dir / 'avb.key',
    )
    parser.add_argument(
        '--sign-key-ota',
        type=Path,
        help='OTA private key file for signing output OTA',
        default=default_keys_dir / 'ota.key',
    )
    parser.add_argument(
        '--sign-cert-ota',
        type=Path,
        help='OTA certificate file for signing output OTA',
        default=default_keys_dir / 'ota.crt',
    )
    parser.add_argument(
        '--pass-avb-env-var',
        type=str,
        help='Private key passphrase environment variable for AVB signing key',
    )
    parser.add_argument(
        '--pass-ota-env-var',
        type=str,
        help='Private key passphrase environment variable for OTA signing key',
    )
    parser.add_argument(
        '--pass-avb-file',
        type=Path,
        help='Private key passphrase file for AVB signing key',
    )
    parser.add_argument(
        '--pass-ota-file',
        type=Path,
        help='Private key passphrase file for OTA signing key',
    )
    parser.add_argument(
        '--patch-arg',
        action='append',
        help='Extra argument to pass to `avbroot ota patch`',
    )

    for name in modules.all_modules():
        parser.add_argument(
            f'--module-{name}',
            nargs='?',
            const=True,
            type=Path,
            default=None,
            help=f'{name} module zip. If path omitted, it will be automatically downloaded.',
        )

    parser.add_argument(
        '--debug-shell',
        action='store_true',
        help='Spawn a debug shell before cleaning up temporary directory',
    )


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


def get_ota_metadata(ota: Path) -> dict[str, str]:
    props: dict[str, str] = {}

    with zipfile.ZipFile(ota, 'r') as z:
        with z.open('META-INF/com/android/metadata', 'r') as f:
            for line in f:
                line = line.decode('UTF-8').strip()

                key, delim, value = line.partition('=')
                if not delim:
                    raise ValueError(f'Bad OTA metadata line: {line!r}')

                props[key] = value

    return props


def command_patch(args: argparse.Namespace, temp_dir: Path, binaries_dir: Path):
    logger.info("Patching OTA...")

    # Set advanced args defaults

    if args.output is None:
        args.output = Path(f'{args.input}.patched')

    if args.patch_arg is None:
        args.patch_arg = ['--rootless']

    sign_key_avb = external.SigningKey(
        args.sign_key_avb,
        args.pass_avb_env_var,
        args.pass_avb_file,
    )
    sign_key_ota = external.SigningKey(
        args.sign_key_ota,
        args.pass_ota_env_var,
        args.pass_ota_file,
    )

    inject_modules: list[modules.Module] = []
    need_boot_fs: set[str] = set()
    need_ext_fs: set[str] = set()
    need_sepolicies = False

    # Get OTA partitions
    partitions = external.list_ota(args.input)

    # Non GKI-2.0 devices such as the Pixel 4a contain sepolicies on boot partition
    sepolicies_partition = 'vendor_boot' if ('vendor_boot' in partitions) else 'boot'

    for name, module in modules.create_modules(binaries_dir, args).items():
        logger.info(f'Will be injecting module {name}')
        inject_modules.append(module)

        requirements = module.requirements()
        need_boot_fs |= requirements.boot_images
        need_ext_fs |= requirements.ext_images
        need_sepolicies |= requirements.selinux_patching

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
        external.pack_avb(paths.image, paths.unpacked, sign_key_avb, True)

    # Repack boot images.
    for name, fs in boot_fs.items():
        paths = BootImagePaths(images_dir, temp_dir, name)

        with open(paths.metadata, 'w') as f:
            tomlkit.dump(fs.info.model_dump(exclude_none=True), f)

        external.pack_cpio(paths.ramdisk, paths.unpacked)
        external.pack_boot(paths.raw_image, paths.unpacked)
        external.pack_avb(paths.image, paths.unpacked, sign_key_avb, False)

    # Patch OTA.
    external.patch_ota(
        args.input,
        args.output,
        sign_key_avb,
        sign_key_ota,
        args.sign_cert_ota,
        {name: images_dir / f'{name}.img' for name in boot_fs | ext_fs},
        args.patch_arg,
    )

    if args.generate_custota:
        # Generate Custota csig.
        external.generate_csig(args.output, sign_key_ota, args.sign_cert_ota)

        # Generate Custota update-info.
        codename = get_ota_metadata(args.output)['pre-device']
        update_info = args.output.parent / f'{codename}.json'
        external.generate_update_info(update_info, args.output.name)
