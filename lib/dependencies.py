import logging
import os
import shutil
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path

import requests

# https://codeberg.org/chenxiaolong/chenxiaolong
# https://gitlab.com/chenxiaolong/chenxiaolong
# https://github.com/chenxiaolong/chenxiaolong
SSH_PUBLIC_KEY_CHENXIAOLONG = \
    'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDOe6/tBnO7xZhAWXRj3ApUYgn+XZ0wnQiXM8B7tPgv4'

logger = logging.getLogger(__name__)


def _download_chenxiaolong_binary(
    binaries_dir: Path,
    repo: str,
    version: str,
    artifact: str | None = None,
) -> Path:
    if artifact is None:
        artifact = repo

    out = binaries_dir / artifact

    if out.exists():
        return out

    with tempfile.NamedTemporaryFile() as zipped:
        url = f'https://github.com/chenxiaolong/{repo}/releases/download/v{version}/{artifact}-{version}-x86_64-unknown-linux-gnu.zip'
        _download_chenxiaolong_inner(Path(zipped.name), url, name=artifact)

        logger.debug(f'Unzipping {artifact} artifact')
        if not binaries_dir.exists():
            binaries_dir.mkdir()
        with zipfile.ZipFile(zipped, 'r') as archive:
            archive.extract(artifact, binaries_dir)

    logger.debug(f'Setting {artifact} as executable')
    os.chmod(out, os.stat(out).st_mode | stat.S_IXUSR | stat.S_IXGRP)

    logger.info(f'Finished downloading {repo}')
    return out


def _download_chenxiaolong_module(
    modules_dir: Path,
    repo: str,
    version: str,
) -> Path:
    file = modules_dir / f'{repo}-{version}.zip'

    if file.exists():
        return file

    logger.info(f'Downloading {repo} with version {version}')
    url = f'https://github.com/chenxiaolong/{repo}/releases/download/v{version}/{repo}-{version}-release.zip'
    _download_chenxiaolong_inner(file, url, name=repo)

    logger.info(f'Finished downloading {repo}')
    return file


def _download_chenxiaolong_inner(file: Path, url: str, name: str):
    try:
        with requests.get(url, stream=True) as resp:
            resp.raise_for_status()
            with open(file, 'wb') as f:
                shutil.copyfileobj(resp.raw, f)
    except Exception as e:
        raise IOError(f'Failed to download {name} artifact zip') from e

    try:
        logger.info(f'Downloading {name} signature')
        with requests.get(f'{url}.sig') as resp:
            resp.raise_for_status()
            artifact_sig = resp.text
        logger.debug(f'Obtained {name} artifact signature:\n{resp.text}')
    except Exception as e:
        raise IOError(f'Failed to download {name} artifact signature') from e

    logger.info(f'Verifying {name} signature')
    try:
        with (tempfile.NamedTemporaryFile('w') as signers_file,
              tempfile.NamedTemporaryFile('w') as signature_file,
              open(file, 'rb') as payload_file):

            signers_file.write(f'chenxiaolong {SSH_PUBLIC_KEY_CHENXIAOLONG}')
            signers_file.flush()
            signature_file.write(artifact_sig)
            signature_file.flush()

            subprocess.check_call([
                'ssh-keygen',
                '-Y', 'verify',
                '-I', 'chenxiaolong',
                '-f', signers_file.name,
                '-s', signature_file.name,
                '-n', 'file',
                file.absolute()
            ], stdin=payload_file)
    except Exception as e:
        raise Exception(f'Failed to verify {name} artifact signature') from e


# Download avbroot with a minimum version of 3.30.0
def download_avbroot(binaries_dir: Path):
    _download_chenxiaolong_binary(binaries_dir, 'avbroot', '3.30.0')


def download_afsr(binaries_dir: Path):
    _download_chenxiaolong_binary(binaries_dir, 'afsr', '1.0.4')


def download_custota_tool(binaries_dir: Path):
    return _download_chenxiaolong_binary(binaries_dir, 'Custota', '6.1', 'custota-tool')


def download_alterinstaller(binaries_dir: Path):
    return _download_chenxiaolong_module(binaries_dir, 'AlterInstaller', '2.3')


def download_bcr(modules_dir: Path) -> Path:
    return _download_chenxiaolong_module(modules_dir, 'BCR', "3.1")


def download_custota(modules_dir: Path) -> Path:
    return _download_chenxiaolong_module(modules_dir, 'Custota', "6.1")


def download_msd(modules_dir: Path) -> Path:
    return _download_chenxiaolong_module(modules_dir, 'MSD', "2.0")


def download_oemunlockonboot(modules_dir: Path) -> Path:
    return _download_chenxiaolong_module(modules_dir, 'OEMUnlockOnBoot', "1.3")
