"""Tests for the encryption module."""

from __future__ import annotations

import pytest

from pdf_stego.encryption import decrypt, encrypt


class TestAesEncryption:
    """AES-256-GCM encryption tests."""

    def test_roundtrip(self) -> None:
        data = b"Hello, PDF steganography!"
        key = "my-secret-key"
        encrypted = encrypt(data, "aes", key)
        decrypted = decrypt(encrypted, "aes", key)
        assert decrypted == data

    def test_roundtrip_empty(self) -> None:
        data = b""
        key = "key"
        encrypted = encrypt(data, "aes", key)
        decrypted = decrypt(encrypted, "aes", key)
        assert decrypted == data

    def test_roundtrip_binary(self) -> None:
        data = bytes(range(256))
        key = "binary-test"
        encrypted = encrypt(data, "aes", key)
        decrypted = decrypt(encrypted, "aes", key)
        assert decrypted == data

    def test_different_key_fails(self) -> None:
        data = b"secret data"
        encrypted = encrypt(data, "aes", "correct-key")
        with pytest.raises(Exception, match=r".*"):
            decrypt(encrypted, "aes", "wrong-key")

    def test_ciphertext_differs_from_plaintext(self) -> None:
        data = b"plaintext message"
        encrypted = encrypt(data, "aes", "key")
        # Ciphertext should not contain the plaintext
        assert data not in encrypted

    def test_different_encryptions_differ(self) -> None:
        """Two encryptions of the same data produce different ciphertexts (random IV/salt)."""
        data = b"test"
        key = "key"
        enc1 = encrypt(data, "aes", key)
        enc2 = encrypt(data, "aes", key)
        assert enc1 != enc2  # Random salt + nonce


class TestNoEncryption:
    """Passthrough when encryption='none'."""

    def test_passthrough(self) -> None:
        data = b"unencrypted"
        assert encrypt(data, "none", "") == data
        assert decrypt(data, "none", "") == data
