import argparse
import base64
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)
default_keys_dir = Path(os.getcwd()) / '.keys'


def args_encode_keys(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        'encode-keys',
        help='Encodes all necessary signing keys as base64 to be used as environment variables',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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


def command_encode_keys(args: argparse.Namespace):
    logger.info('Encoding signing keys...')

    with args.sign_key_avb.open('rb') as f:
        sign_key_avb = base64.standard_b64encode(f.read()).decode('utf-8')
    with args.sign_key_ota.open('rb') as f:
        sign_key_ota = base64.standard_b64encode(f.read()).decode('utf-8')
    with args.sign_cert_ota.open('rb') as f:
        sign_cert_ota = base64.standard_b64encode(f.read()).decode('utf-8')

    logger.info('Add these to your CI, if necessary. '
                'This script takes the keys and their passwords as either files or environment variables!\n\n'
                f'KEY_AVB_BASE64={sign_key_avb}\n\n'
                f'KEY_OTA_BASE64={sign_key_ota}\n\n'
                f'CERT_OTA_BASE64={sign_cert_ota}\n\n')
