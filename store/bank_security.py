
import os

from cryptography.fernet import Fernet, InvalidToken
from django.core.exceptions import ImproperlyConfigured


def get_bank_cipher():
    key = os.environ.get('GLOWCART_BANK_ENCRYPTION_KEY')

    if not key:
        raise ImproperlyConfigured(
            'GLOWCART_BANK_ENCRYPTION_KEY is not configured.'
        )

    try:
        return Fernet(key.encode('utf-8'))
    except (ValueError, TypeError):
        raise ImproperlyConfigured(
            'GLOWCART_BANK_ENCRYPTION_KEY is invalid.'
        )


def encrypt_bank_value(value):
    if not value:
        return ''

    cipher = get_bank_cipher()
    return cipher.encrypt(value.encode('utf-8')).decode('utf-8')


def decrypt_bank_value(value):
    if not value:
        return ''

    cipher = get_bank_cipher()

    try:
        return cipher.decrypt(value.encode('utf-8')).decode('utf-8')
    except (InvalidToken, ValueError, TypeError):
        raise ImproperlyConfigured(
            'Unable to decrypt bank details. Check the encryption key.'
        )
