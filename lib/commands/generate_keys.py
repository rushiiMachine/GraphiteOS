import argparse
import logging
from pathlib import Path

from lib import external
from lib.external import KeyFile, InputFile, KEYS_DIR

logger = logging.getLogger(__name__)


# noinspection DuplicatedCode
def register(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        'generate-keys',
        help='Generate all the necessary OTA signing keys',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        allow_abbrev=False,
        suggest_on_error=True,
    )

    parser.add_argument(
        '--signing-key-avb',
        help='Output AVB private key file.',
        metavar='<avb.key>',
        type=Path,
        default=KEYS_DIR / 'avb.key',
    )
    parser.add_argument(
        '--flashing-key-avb',
        help='Output flashable avb_custom_key file.',
        metavar='<avb_pkmd.bin>',
        type=Path,
        default=KEYS_DIR / 'avb_pkmd.bin',
    )
    parser.add_argument(
        '--signing-key-ota',
        help='Output OTA private key file.',
        metavar='<ota.key>',
        type=Path,
        default=KEYS_DIR / 'ota.key',
    )
    parser.add_argument(
        '--signing-cert-ota',
        help='Output OTA certificate file.',
        metavar='<ota.crt>',
        type=Path,
        default=KEYS_DIR / 'ota.crt',
    )
    parser.add_argument(
        '--signing-cert-subject',
        help='OTA certificate subject name.',
        metavar='<SUBJECT>',
        type=str,
        default='CN=avbroot'
    )

    group_signing_key_avb_password = parser.add_mutually_exclusive_group()
    group_signing_key_avb_password.add_argument(
        '--signing-key-avb-password-file',
        help='AVB private key password file.',
        metavar='<FILE>',
        type=Path,
    )
    group_signing_key_avb_password.add_argument(
        '--signing-key-avb-password-env',
        help='Environment variable containing the base64-encoded AVB private key password.',
        metavar='<ENVIRONMENT_VARIABLE>',
        type=str,
    )

    group_signing_key_ota_password = parser.add_mutually_exclusive_group()
    group_signing_key_ota_password.add_argument(
        '--signing-key-ota-password-file',
        help='OTA private key password file.',
        metavar='<FILE>',
        type=Path,
    )
    group_signing_key_ota_password.add_argument(
        '--signing-key-ota-password-env',
        help='Environment variable containing the base64-encoded OTA private key password.',
        metavar='<ENVIRONMENT_VARIABLE>',
        type=str,
    )


def run(args: argparse.Namespace, _temp_dir: Path):
    logger.info('Generating signing keys...')

    flashing_key_avb: Path = args.flashing_key_avb
    signing_key_avb = KeyFile(
        input_env=None,
        input_file=args.signing_key_avb,
        pass_env=args.signing_key_avb_password_env,
        pass_file=args.signing_key_avb_password_file,
    )
    signing_key_ota = KeyFile(
        input_env=None,
        input_file=args.signing_key_ota,
        pass_env=args.signing_key_ota_password_env,
        pass_file=args.signing_key_ota_password_file,
    )
    signing_cert_ota = InputFile(
        input_env=None,
        input_file=args.signing_cert_ota,
    )

    assert signing_key_avb.input_file is not None
    assert signing_key_ota.input_file is not None
    assert signing_cert_ota.input_file is not None

    for file in [flashing_key_avb, signing_key_avb.input_file,
                 signing_key_ota.input_file, signing_cert_ota.input_file]:

        file.parent.mkdir(parents=True, exist_ok=True)

        if file.exists():
            logger.error(f'Will not overwrite existing keyfile {file}')
            exit(1)

    logger.info('Generating AVB private signing key')
    external.generate_key(signing_key_avb)
    logger.info('Generating OTA private signing key')
    external.generate_key(signing_key_ota)
    logger.info('Generating OTA certificate')
    external.generate_cert(
        out=signing_cert_ota.input_file,
        key_ota=signing_key_ota,
        subject=args.signing_cert_subject,
    )
    logger.info('Encoding AVB public key')
    external.encode_avb_key(
        out=flashing_key_avb,
        key_avb=signing_key_avb,
    )

    logger.info('Successfully generated keys! Make sure to create a backup prior to relocking your bootloader!\n'
                f'    AVB public key:  {flashing_key_avb}\n'
                f'    AVB private key: {signing_key_avb.input_file}\n'
                f'    OTA private key: {signing_key_ota.input_file}\n'
                f'    OTA certificate: {signing_cert_ota.input_file}')
