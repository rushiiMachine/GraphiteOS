import argparse
import logging
import os
from pathlib import Path

from lib import external

logger = logging.getLogger(__name__)
default_keys_dir = Path(os.getcwd()) / '.keys'


def args_keys(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        'keys',
        help='Generates all signing keys',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        '--sign-key-avb',
        type=Path,
        help='Output AVB private key file for signing output OTA',
        default=default_keys_dir / 'avb.key',
    )
    parser.add_argument(
        '--flashing-key-avb',
        type=Path,
        help='Output AVB public key file to be flashed onto the device',
        default=default_keys_dir / 'avb_pkmd.bin',
    )
    parser.add_argument(
        '--sign-key-ota',
        type=Path,
        help='Output OTA private key file for signing output OTA',
        default=default_keys_dir / 'ota.key',
    )
    parser.add_argument(
        '--sign-cert-ota',
        type=Path,
        help='Output OTA certificate file for signing output OTA',
        default=default_keys_dir / 'ota.crt',
    )
    parser.add_argument(
        '--sign-cert-subject',
        type=str,
        help='OTA certificate subject name',
        default='CN=avbroot'
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


def command_keys(args: argparse.Namespace):
    logger.info('Generating signing keys...')

    avb_public_key = args.flashing_key_avb
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
    sign_cert_ota = args.sign_cert_ota
    sign_cert_subject = args.sign_cert_subject

    for file in [avb_public_key, sign_key_avb.key, sign_key_ota.key, sign_cert_ota]:
        if file.exists():
            logger.error(f'Will not overwrite existing keyfile {file}')
            exit(1)

        file.parent.mkdir(parents=True, exist_ok=True)

    logger.info('Generating AVB private signing key')
    external.generate_key(sign_key_avb)
    logger.info('Generating OTA private signing key')
    external.generate_key(sign_key_ota)
    logger.info('Generating OTA certificate')
    external.generate_cert(sign_cert_ota, sign_key_ota, sign_cert_subject)
    logger.info('Encoding AVB public key')
    external.encode_avb_key(avb_public_key, sign_key_avb)

    logger.info('Successfully generated keys! Make sure to create a backup prior to relocking your bootloader!\n'
                f'    AVB public key:  {avb_public_key}\n'
                f'    AVB private key: {sign_key_avb.key}\n'
                f'    OTA private key: {sign_key_ota.key}\n'
                f'    OTA certificate: {sign_cert_ota}')
