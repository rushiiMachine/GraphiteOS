# SPDX-FileCopyrightText: 2024-2025 Andrew Gunnerson
# SPDX-License-Identifier: GPL-3.0-only

import logging
import os
import subprocess
import tempfile
from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)

"""
Directory relative to current working directory in which
to download all executable binary tools and module files.
"""
BINARIES_DIR = Path(os.getcwd()) / '.bin'

"""Default directory to store signing keys"""
KEYS_DIR = Path(os.getcwd()) / '.keys'


@dataclass
class InputFile:
    input_env: str | None
    input_file: Path | None

    @contextmanager
    def get_file(self) -> Generator[Path, Any, None]:
        """
        Returns a file containing this input file.
        If the source was an environment variable, it is written to a temporary
        file and deleted upon being released.
        """
        if self.input_env is not None:
            if len(self.input_env) == 0:
                raise ValueError(f'Specified environment variable is invalid!')

            data = os.getenv(self.input_env)

            if data is None or len(self.input_env) == 0:
                raise ValueError(f'Specified environment variable {self.input_env} is empty!')

            with tempfile.NamedTemporaryFile("w") as f:
                f.write(data)
                f.flush()
                yield Path(f.name)
        elif self.input_file is not None:
            if not self.input_file.is_file():
                raise FileNotFoundError(f'Specified input file does not exist: {self.input_file}')

            yield self.input_file
        else:
            raise ValueError('Input file does not contain any input sources!')


@dataclass
class KeyFile(InputFile):
    pass_env: str | None = None
    pass_file: Path | None = None


def list_ota(ota: Path) -> list[str]:
    logger.info(f'Listing OTA partitions: {ota}')

    cmd = [
        'avbroot', 'ota', 'list',
        '--input', ota,
    ]

    return (subprocess.check_output(cmd)
            .decode()
            .splitlines())


def verify_ota(ota: Path, public_key_avb: Path | None, cert_ota: Path | None):
    logger.info(f'Verifying OTA: {ota}')

    cmd = [
        'avbroot', 'ota', 'verify',
        '--input', ota,
    ]

    if public_key_avb:
        cmd += ['--public-key-avb', public_key_avb]
    if cert_ota:
        cmd += ['--cert-ota', cert_ota]

    subprocess.check_call(cmd)


def unpack_ota(ota: Path, output_dir: Path, partitions: Iterable[str]):
    logger.info(f'Unpacking OTA: {ota}')

    cmd = [
        'avbroot', 'ota', 'extract',
        '--input', ota,
        '--directory', output_dir,
    ]

    for partition in partitions:
        cmd += ['--partition', partition]

    subprocess.check_call(cmd)


def patch_ota(
    input_ota: Path,
    output_ota: Path,
    key_avb: KeyFile,
    key_ota: KeyFile,
    cert_ota: InputFile,
    replace: dict[str, Path],
    extra_args: Sequence[str],
):
    image_names = ', '.join(sorted(replace.keys())) if replace else '(none)'
    logger.info(f'Patching OTA with replaced images: {image_names}: {output_ota}')

    cmd = [
        'avbroot', 'ota', 'patch',
        '--input', input_ota,
        '--output', output_ota,
    ]

    for k, v in replace.items():
        cmd += ['--replace', k, v]

    if key_avb.pass_env is not None:
        cmd += ['--pass-avb-env-var', key_avb.pass_env]
    elif key_avb.pass_file is not None:
        cmd += ['--pass-avb-file', key_avb.pass_file]

    if key_ota.pass_env is not None:
        cmd += ['--pass-ota-env-var', key_ota.pass_env]
    elif key_ota.pass_file is not None:
        cmd += ['--pass-ota-file', key_ota.pass_file]

    with (key_avb.get_file() as avb_key_file,
          key_ota.get_file() as ota_key_file,
          cert_ota.get_file() as ota_cert_file):

        cmd += [
            '--key-avb', avb_key_file,
            '--key-ota', ota_key_file,
            '--cert-ota', ota_cert_file,
            *extra_args,
        ]

        subprocess.check_call(cmd)


def unpack_avb(image: Path, output_dir: Path):
    logger.info(f'Unpacking AVB image: {image}')

    subprocess.check_call([
        'avbroot', 'avb', 'unpack',
        '--quiet',
        '--input', image.absolute(),
    ], cwd=output_dir)


def pack_avb(
    image: Path,
    input_dir: Path,
    key: KeyFile,
    recompute_size: bool,
):
    logger.info(f'Packing AVB image: {image}')

    cmd = [
        'avbroot', 'avb', 'pack',
        '--quiet',
        '--output', image.absolute(),
    ]

    if recompute_size:
        cmd += ['--recompute-size']

    if key.pass_env is not None:
        cmd += ['--pass-env-var', key.pass_env]
    elif key.pass_file is not None:
        cmd += ['--pass-file', key.pass_file]

    with key.get_file() as key_file:
        cmd += ['--key', key_file]

        subprocess.check_call(cmd, cwd=input_dir)


def unpack_boot(image: Path, output_dir: Path):
    logger.info(f'Unpacking boot image: {image}')

    subprocess.check_call([
        'avbroot', 'boot', 'unpack',
        '--quiet',
        '--input', image.absolute(),
    ], cwd=output_dir)


def pack_boot(image: Path, input_dir: Path):
    logger.info(f'Packing boot image: {image}')

    subprocess.check_call([
        'avbroot', 'boot', 'pack',
        '--quiet',
        '--output', image.absolute(),
    ], cwd=input_dir)


def unpack_cpio(archive: Path, output_dir: Path):
    logger.info(f'Unpacking CPIO archive: {archive}')

    subprocess.check_call([
        'avbroot', 'cpio', 'unpack',
        '--quiet',
        '--input', archive.absolute(),
    ], cwd=output_dir)


def pack_cpio(archive: Path, input_dir: Path):
    logger.info(f'Packing CPIO archive: {archive}')

    subprocess.check_call([
        'avbroot', 'cpio', 'pack',
        '--quiet',
        '--output', archive.absolute(),
    ], cwd=input_dir)


def unpack_fs(image: Path, output_dir: Path):
    logger.info(f'Unpacking filesystem: {image}')

    subprocess.check_call([
        'afsr', 'unpack',
        '--input', image.absolute(),
    ], cwd=output_dir)


def pack_fs(image: Path, input_dir: Path):
    logger.info(f'Packing filesystem: {image}')

    subprocess.check_call([
        'afsr', 'pack',
        '--output', image.absolute(),
    ], cwd=input_dir)


def generate_csig(ota: Path, key_ota: KeyFile, cert_ota: InputFile):
    logger.info(f'Generating Custota csig: {ota}.csig')

    cmd = [
        'custota-tool', 'gen-csig',
        '--input', ota,
    ]

    if key_ota.pass_env is not None:
        cmd += ['--passphrase-env-var', key_ota.pass_env]
    elif key_ota.pass_file is not None:
        cmd += ['--passphrase-file', key_ota.pass_file]

    with (key_ota.get_file() as key_file,
          cert_ota.get_file() as cert_file):
        cmd += ['--key', key_file,
                '--cert', cert_file]

        subprocess.check_call(cmd)


def generate_update_info(update_info: Path, location: str):
    logger.info(f'Generating Custota update info: {update_info}')

    subprocess.check_call([
        'custota-tool', 'gen-update-info',
        '--file', update_info,
        '--location', location,
    ])


def generate_key(key: KeyFile):
    assert key.input_file is not None, "Provided key info must contain target output file!"

    cmd = [
        'avbroot', 'key', 'generate-key',
        '--output', key.input_file.absolute(),
    ]

    if key.pass_env is not None:
        cmd += ['--pass-env-var', key.pass_env]
    elif key.pass_file is not None:
        cmd += ['--pass-file', key.pass_file]

    subprocess.check_call(cmd)


def generate_cert(out: Path, key_ota: KeyFile, subject: str | None = None):
    logger.info(f'Generating cert')

    cmd = [
        'avbroot', 'key', 'generate-cert',
        '--validity', '36500',  # 100 years
        '--output', out.absolute(),
    ]

    if subject is not None:
        cmd += ['--subject', subject]

    if key_ota.pass_env is not None:
        cmd += ['--pass-env-var', key_ota.pass_env]
    elif key_ota.pass_file is not None:
        cmd += ['--pass-file', key_ota.pass_file]

    with key_ota.get_file() as key_file:
        cmd += ['--key', key_file.absolute()]

        subprocess.check_call(cmd)


def encode_avb_key(out: Path, key_avb: KeyFile):
    logger.info(f'Encoding AVB key')

    cmd = [
        'avbroot', 'key', 'encode-avb',
        '--output', out.absolute(),
    ]

    if key_avb.pass_env is not None:
        cmd += ['--pass-env-var', key_avb.pass_env]
    elif key_avb.pass_file is not None:
        cmd += ['--pass-file', key_avb.pass_file]

    with key_avb.get_file() as key_file:
        cmd += ['--key', key_file.absolute()]

        subprocess.check_call(cmd)
