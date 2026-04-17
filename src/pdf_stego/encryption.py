"""Watermark encryption backends.

Supports AES-256-GCM (via the ``cryptography`` library).
"""

from __future__ import annotations

import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from pdf_stego.types import EncryptionMethod

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def encrypt(data: bytes, method: EncryptionMethod, key: str) -> bytes:
    """Encrypt *data* using the specified *method*.

    Args:
        data: Raw watermark bytes to encrypt.
        method: ``"none"`` or ``"aes"``.
        key: Passphrase / key string.

    Returns:
        Encrypted bytes.
    """
    if method == "none":
        return data
    if method == "aes":
        return _aes_encrypt(data, key)
    raise ValueError(f"Unknown encryption method: {method!r}")


def decrypt(data: bytes, method: EncryptionMethod, key: str) -> bytes:
    """Decrypt *data* using the specified *method*.

    Args:
        data: Encrypted bytes.
        method: ``"none"`` or ``"aes"``.
        key: Passphrase / key string used during encryption.

    Returns:
        Decrypted bytes.
    """
    if method == "none":
        return data
    if method == "aes":
        return _aes_decrypt(data, key)
    raise ValueError(f"Unknown encryption method: {method!r}")


# ---------------------------------------------------------------------------
# AES-256-GCM via ``cryptography``
# ---------------------------------------------------------------------------

_AES_SALT_LEN = 16
_AES_NONCE_LEN = 12  # 96-bit nonce recommended for GCM
_AES_KEY_LEN = 32  # 256-bit key
_AES_KDF_ITERATIONS = 480_000


def _derive_aes_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_AES_KEY_LEN,
        salt=salt,
        iterations=_AES_KDF_ITERATIONS,
    )
    return bytes(kdf.derive(passphrase.encode("utf-8")))


def _aes_encrypt(data: bytes, passphrase: str) -> bytes:
    salt = os.urandom(_AES_SALT_LEN)
    key = _derive_aes_key(passphrase, salt)
    nonce = os.urandom(_AES_NONCE_LEN)
    aesgcm = AESGCM(key)
    ciphertext: bytes = aesgcm.encrypt(nonce, data, None)
    # Layout: salt || nonce || ciphertext+tag
    return salt + nonce + ciphertext


def _aes_decrypt(data: bytes, passphrase: str) -> bytes:
    min_len = _AES_SALT_LEN + _AES_NONCE_LEN + 16  # 16-byte GCM tag minimum
    if len(data) < min_len:
        raise ValueError("Ciphertext too short for AES-GCM decryption")
    salt = data[:_AES_SALT_LEN]
    nonce = data[_AES_SALT_LEN : _AES_SALT_LEN + _AES_NONCE_LEN]
    ciphertext = data[_AES_SALT_LEN + _AES_NONCE_LEN :]
    key = _derive_aes_key(passphrase, salt)
    aesgcm = AESGCM(key)
    return bytes(aesgcm.decrypt(nonce, ciphertext, None))
