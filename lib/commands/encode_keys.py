import argparse
import base64
import logging
from pathlib import Path

from lib.external import KEYS_DIR

logger = logging.getLogger(__name__)


def register(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        'encode-keys',
        help='Encode OTA signing keys to be used as environment variables in CI',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        allow_abbrev=False,
        suggest_on_error=True,
    )

    parser.add_argument(
        '--signing-key-avb',
        help='AVB private key file for signing output OTA.',
        metavar='<avb.key>',
        type=Path,
        default=KEYS_DIR / 'avb.key'
    )
    parser.add_argument(
        '--signing-key-ota',
        help='OTA private key file for signing output OTA.',
        metavar='<ota.key>',
        type=Path,
        default=KEYS_DIR / 'ota.key'
    )
    parser.add_argument(
        '--signing-cert-ota',
        help='OTA certificate file for signing output OTA.',
        metavar='<ota.crt>',
        type=Path,
        default=KEYS_DIR / 'ota.crt'
    )


def run(args: argparse.Namespace, _temp_dir: Path):
    logger.info('Encoding signing keys...')

    with args.signing_key_avb.open('rb') as f:
        sign_key_avb = base64.standard_b64encode(f.read()).decode('utf-8')
    with args.signing_key_ota.open('rb') as f:
        sign_key_ota = base64.standard_b64encode(f.read()).decode('utf-8')
    with args.signing_cert_ota.open('rb') as f:
        sign_cert_ota = base64.standard_b64encode(f.read()).decode('utf-8')

    logger.info('Add these to your CI, if necessary. '
                'This script takes the keys and their passwords as either files or environment variables!\n\n'
                f'KEY_AVB_BASE64={sign_key_avb}\n\n'
                f'KEY_OTA_BASE64={sign_key_ota}\n\n'
                f'CERT_OTA_BASE64={sign_cert_ota}\n\n')
