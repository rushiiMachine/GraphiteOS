import argparse
import hashlib
import logging
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import override

from cryptography import x509

from lib.filesystem import CpioFs, ExtFs
from lib.modules import Module, ModuleRequirements

logger = logging.getLogger(__name__)

CA_CERTS_PATH = '/system/etc/security/cacerts'
CA_CERTS_SEPOLICY = 'u:object_r:system_security_cacerts_file:s0'

CA_CERTS_GOOGLE_PATH = '/system/etc/security/cacerts_google'
CA_CERTS_GOOGLE_SEPOLICY = 'u:object_r:system_file:s0'


# TODO: patch com.android.conscrypt apex module on Android 14 to inject cacerts


class SystemCertsModule(Module):
    def __init__(self, certs: list[Path]) -> None:
        super().__init__()

        self.certs: set[Path] = set(certs)

    @override
    @staticmethod
    def create(args: argparse.Namespace) -> SystemCertsModule | None:
        certs: list[Path] | None = args.module_system_certs

        if certs is None or len(certs) == 0:
            return None

        return SystemCertsModule(certs)

    @override
    @staticmethod
    def register_args(parser: argparse._ActionsContainer):
        parser.add_argument(
            '--module-system-certs',
            help='Adds a certificate to the system trust store.\n'
                 'This allows your custom OTA server used by Custota to present a self-signed certificate.\n'
                 'See the README for more details.',
            metavar='<CERT_FILE>',
            type=Path,
            nargs='+',
        )

    @override
    @staticmethod
    def requirements() -> ModuleRequirements:
        return ModuleRequirements(
            boot_images=set(),
            ext_images={'system'},
            selinux_patching=False,
        )

    @override
    def inject(
        self,
        boot_fs: dict[str, CpioFs],
        ext_fs: dict[str, ExtFs],
        sepolicies: Iterable[Path],
    ) -> None:
        logger.info('Injecting certificates into system trust store:'
                    '\n  ' + '\n  '.join(str(path) for path in self.certs))

        system_fs = ext_fs['system']

        for cert in self.certs:
            _add_certificate(system_fs, cert)


def _add_certificate(system_fs: ExtFs, cert_file: Path):
    if not cert_file.is_file():
        raise FileNotFoundError(f'Specified certificate file does not exist: {cert_file}')

    try:
        with cert_file.open('rb') as f:
            cert = x509.load_pem_x509_certificate(f.read())
    except Exception as e:
        raise ValueError(f'Failed to parse specified certificate: {cert_file}') from e

    subject_der = cert.subject.public_bytes()
    subject_md5 = hashlib.md5(subject_der).digest()

    short_value = int.from_bytes(subject_md5[:4], "little")
    short_hash = f"{short_value:08x}"

    def copy_cert(target_dir: Path, sepolicy: str | None = None):
        path = target_dir / _find_cert_name(system_fs, CA_CERTS_PATH, short_hash)

        if not system_fs.exists(CA_CERTS_PATH):
            return

        with cert_file.open('rb') as src:
            with system_fs.open(path, 'wb', label=sepolicy) as dst:
                shutil.copyfileobj(src, dst)

    copy_cert(Path(CA_CERTS_PATH), CA_CERTS_SEPOLICY)
    copy_cert(Path(CA_CERTS_GOOGLE_PATH), CA_CERTS_GOOGLE_SEPOLICY)

    # TODO: patch apex com.android.conscrypt /cacerts module


def _find_cert_name(system_fs: ExtFs, certs_dir: str, prefix: str) -> str:
    n = 0
    while system_fs.exists(f'{certs_dir}/{prefix}.{n}'):
        n += 1
    return f'{prefix}.{n}'
