import argparse
from pathlib import Path

from lib.external import KEYS_DIR


# noinspection DuplicatedCode
def register_keys_args(parser: argparse.ArgumentParser):
    group_keys = parser.add_argument_group(
        title='Keys',
        description='Signing keys & certificates for generating re-signed OTAs.'
    )

    group_signing_key_avb = group_keys.add_mutually_exclusive_group(required=True)
    group_signing_key_avb.add_argument(
        '--signing-key-avb',
        help='AVB private key file for signing output OTA.',
        metavar='<avb.key>',
        type=Path,
        default=KEYS_DIR / 'avb.key'
    )
    group_signing_key_avb.add_argument(
        '--signing-key-avb-env',
        help='Environment variable containing a base64-encoded AVB private key.',
        metavar='<ENVIRONMENT_VARIABLE>',
        type=str,
    )

    group_signing_key_ota = group_keys.add_mutually_exclusive_group(required=True)
    group_signing_key_ota.add_argument(
        '--signing-key-ota',
        help='OTA private key file for signing output OTA.',
        metavar='<ota.key>',
        type=Path,
        default=KEYS_DIR / 'ota.key'
    )
    group_signing_key_ota.add_argument(
        '--signing-key-ota-env',
        help='Environment variable containing a base64-encoded OTA private key.',
        metavar='<ENVIRONMENT_VARIABLE>',
        type=str,
    )

    group_signing_cert_ota = group_keys.add_mutually_exclusive_group(required=True)
    group_signing_cert_ota.add_argument(
        '--signing-cert-ota',
        help='OTA certificate file for signing output OTA.',
        metavar='<ota.crt>',
        type=Path,
        default=KEYS_DIR / 'ota.crt'
    )
    group_signing_cert_ota.add_argument(
        '--signing-cert-ota-env',
        help='Environment variable containing a base64-encoded OTA certificate.',
        metavar='<ENVIRONMENT_VARIABLE>',
        type=str,
    )

    group_signing_key_avb_password = group_keys.add_mutually_exclusive_group()
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

    group_signing_key_ota_password = group_keys.add_mutually_exclusive_group()
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
