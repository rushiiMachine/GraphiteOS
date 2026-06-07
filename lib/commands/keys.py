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
    )

    parser.add_argument(
        '--sign-key-avb',
        type=Path,
        help='Path to AVB private key for signing output OTA',
        default=default_keys_dir / 'avb.key',
    )
    parser.add_argument(
        '--flashing-key-avb',
        type=Path,
        help='Path to AVB public key to be flashed onto the device',
        default=default_keys_dir / 'avb_pkmd.bin',
    )
    parser.add_argument(
        '--sign-key-ota',
        type=Path,
        help='Path to OTA private key for signing output OTA',
        default=default_keys_dir / 'ota.key',
    )
    parser.add_argument(
        '--sign-cert-ota',
        type=Path,
        help='Path to OTA certificate for signing output OTA',
        default=default_keys_dir / 'ota.crt',
    )
    parser.add_argument(
        '--sign-cert-subject',
        type=str,
        help='Subject name to be set on the certificate',
        default='CN=avbroot'
    )
    parser.add_argument(
        '--pass-avb-env-var',
        type=str,
        help='Private key passphrase environment variable for AVB signing',
    )
    parser.add_argument(
        '--pass-ota-env-var',
        type=str,
        help='Private key passphrase environment variable for OTA signing',
    )
    parser.add_argument(
        '--pass-avb-file',
        type=Path,
        help='Private key passphrase file for AVB signing',
    )
    parser.add_argument(
        '--pass-ota-file',
        type=Path,
        help='Private key passphrase file for OTA signing',
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

    external.generate_key(sign_key_avb)
    external.generate_key(sign_key_ota)
    external.generate_cert(sign_cert_ota, sign_key_ota, sign_cert_subject)
    external.encode_avb_key(avb_public_key, sign_key_avb)

    logger.info('Successfully generated keys! Make sure to create a backup prior to relocking your bootloader!\n'
                f'    AVB private key: {sign_key_avb.key}\n'
                f'    AVB flashing pubkey: {avb_public_key}\n'
                f'    OTA private key: {sign_key_ota.key}\n'
                f'    OTA certificate: {sign_cert_ota}')
