import io
import logging
import os
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path

import requests

# chenxiaolong's ssh signing key used for tool releases
CHENXIAOLONG_PK = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDOe6/tBnO7xZhAWXRj3ApUYgn+XZ0wnQiXM8B7tPgv4'

logger = logging.getLogger(__name__)


def _download_chenxiaolong(binaries_dir: Path,
                           repo: str,
                           version: str,
                           artifact: str | None = None):
    if artifact is None:
        artifact = repo

    artifact_out = binaries_dir / artifact

    if artifact_out.exists():
        return

    url = f'https://github.com/chenxiaolong/{repo}/releases/download/v{version}/{artifact}-{version}-x86_64-unknown-linux-gnu.zip'
    sig_url = f'{url}.sig'

    try:
        logger.info(f'Downloading {artifact} with version {version}')
        with requests.get(url) as resp:
            resp.raise_for_status()
            artifact_zip = resp.content
    except Exception as e:
        raise IOError(f'Failed to download {artifact} artifact zip') from e

    try:
        logger.info(f'Downloading {artifact} signature')
        with requests.get(sig_url) as resp:
            resp.raise_for_status()
            artifact_sig = resp.text
        logger.debug(f'Obtained {artifact} artifact signature:\n{resp.text}')
    except Exception as e:
        raise IOError(f'Failed to download {artifact} artifact signature') from e

    logger.info(f'Verifying {artifact} signature')
    try:
        with tempfile.NamedTemporaryFile('w') as signers_file, \
                tempfile.NamedTemporaryFile('w') as signature_file, \
                tempfile.NamedTemporaryFile('w+b') as payload_file:
            signers_file.write(f'chenxiaolong {CHENXIAOLONG_PK}')
            signers_file.flush()
            signature_file.write(artifact_sig)
            signature_file.flush()
            payload_file.write(artifact_zip)
            payload_file.flush()
            payload_file.seek(0)

            subprocess.check_call([
                'ssh-keygen',
                '-Y', 'verify',
                '-I', 'chenxiaolong',
                '-f', signers_file.name,
                '-s', signature_file.name,
                '-n', 'file',
            ], stdin=payload_file)
    except Exception as e:
        raise Exception(f'Failed to verify {artifact} artifact signature') from e

    logger.debug(f'Unzipping {artifact} artifact')
    if not binaries_dir.exists():
        binaries_dir.mkdir()
    with zipfile.ZipFile(io.BytesIO(artifact_zip), 'r') as archive:
        archive.extract(artifact, binaries_dir)

    logger.debug(f'Setting {artifact} as executable')
    os.chmod(artifact_out, os.stat(artifact_out).st_mode | stat.S_IXUSR | stat.S_IXGRP)

    logger.info(f'Finished downloading {artifact}')


# Download avbroot with a minimum version of 3.30.0
def download_avbroot(binaries_dir: Path):
    _download_chenxiaolong(binaries_dir, 'avbroot', '3.30.0')


def download_afsr(binaries_dir: Path):
    _download_chenxiaolong(binaries_dir, 'afsr', '1.0.4')


def download_custota_tool(binaries_dir: Path):
    _download_chenxiaolong(binaries_dir, 'custota', '6.1', 'custota-tool')
