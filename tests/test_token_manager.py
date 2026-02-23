"""Tests for TokenManager encryption/decryption."""

import json
import pytest
from cryptography.fernet import InvalidToken

from src.token_manager import TokenManager


class TestTokenManagerKeyGeneration:
    """Tests for key generation."""

    def test_generate_key_returns_string(self):
        """Test that generate_key returns a string."""
        key = TokenManager.generate_key()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_generate_key_is_valid_fernet_key(self):
        """Test that generated key is valid for Fernet."""
        key = TokenManager.generate_key()
        # Should not raise exception
        tm = TokenManager(key)
        assert tm._fernet is not None

    def test_generated_keys_are_different(self):
        """Test that each generated key is different."""
        key1 = TokenManager.generate_key()
        key2 = TokenManager.generate_key()
        assert key1 != key2


class TestTokenManagerInitialization:
    """Tests for TokenManager initialization."""

    def test_init_with_key(self):
        """Test initialization with provided key."""
        key = TokenManager.generate_key()
        tm = TokenManager(key)
        assert tm.key == key
        assert tm._fernet is not None

    def test_init_without_key_raises_error(self):
        """Test that initialization without key raises ValueError."""
        import os
        # Temporarily unset env var
        old_val = os.environ.pop("GARMIN_TOKEN_KEY", None)
        try:
            with pytest.raises(ValueError, match="GARMIN_TOKEN_KEY is required"):
                TokenManager()
        finally:
            if old_val:
                os.environ["GARMIN_TOKEN_KEY"] = old_val

    def test_init_with_key_from_env(self, monkeypatch):
        """Test initialization using environment variable."""
        test_key = TokenManager.generate_key()
        monkeypatch.setenv("GARMIN_TOKEN_KEY", test_key)
        tm = TokenManager()
        assert tm.key == test_key


class TestTokenManagerEncryption:
    """Tests for token encryption."""

    def test_encrypt_returns_bytes(self):
        """Test that encrypt returns bytes."""
        key = TokenManager.generate_key()
        tm = TokenManager(key)
        plaintext = '{"access_token": "test123"}'
        encrypted = tm.encrypt(plaintext)
        assert isinstance(encrypted, bytes)
        assert len(encrypted) > 0

    def test_encrypt_produces_different_ciphertexts(self):
        """Test that same plaintext produces different ciphertexts (due to timestamps)."""
        key = TokenManager.generate_key()
        tm = TokenManager(key)
        plaintext = '{"access_token": "test123"}'
        encrypted1 = tm.encrypt(plaintext)
        encrypted2 = tm.encrypt(plaintext)
        # Fernet includes timestamp, so these should differ
        assert encrypted1 != encrypted2

    def test_encrypt_unicode_string(self):
        """Test encryption of unicode strings."""
        key = TokenManager.generate_key()
        tm = TokenManager(key)
        plaintext = '{"name": "Stéphane", "emoji": "🏃"}'
        encrypted = tm.encrypt(plaintext)
        assert isinstance(encrypted, bytes)


class TestTokenManagerDecryption:
    """Tests for token decryption."""

    def test_decrypt_returns_string(self):
        """Test that decrypt returns a string."""
        key = TokenManager.generate_key()
        tm = TokenManager(key)
        plaintext = '{"access_token": "test123"}'
        encrypted = tm.encrypt(plaintext)
        decrypted = tm.decrypt(encrypted)
        assert isinstance(decrypted, str)

    def test_encrypt_decrypt_roundtrip(self):
        """Test encrypt/decrypt round-trip produces original plaintext."""
        key = TokenManager.generate_key()
        tm = TokenManager(key)
        plaintext = '{"access_token": "test123", "refresh_token": "refresh456"}'
        encrypted = tm.encrypt(plaintext)
        decrypted = tm.decrypt(encrypted)
        assert decrypted == plaintext

    def test_decrypt_json_roundtrip(self):
        """Test round-trip with JSON data."""
        key = TokenManager.generate_key()
        tm = TokenManager(key)
        original_data = {
            "access_token": "token_123",
            "refresh_token": "refresh_456",
            "expires_at": 1234567890,
        }
        plaintext = json.dumps(original_data)
        encrypted = tm.encrypt(plaintext)
        decrypted = tm.decrypt(encrypted)
        recovered_data = json.loads(decrypted)
        assert recovered_data == original_data

    def test_decrypt_invalid_token_raises_error(self):
        """Test that decrypting invalid data raises InvalidToken."""
        key = TokenManager.generate_key()
        tm = TokenManager(key)
        with pytest.raises(InvalidToken):
            tm.decrypt(b"invalid_encrypted_data")

    def test_decrypt_with_wrong_key_raises_error(self):
        """Test that decrypting with wrong key raises InvalidToken."""
        key1 = TokenManager.generate_key()
        key2 = TokenManager.generate_key()
        plaintext = '{"access_token": "test123"}'

        tm1 = TokenManager(key1)
        encrypted = tm1.encrypt(plaintext)

        tm2 = TokenManager(key2)
        with pytest.raises(InvalidToken):
            tm2.decrypt(encrypted)


class TestTokenManagerPadding:
    """Tests for base64 padding handling."""

    def test_key_with_padding(self):
        """Test key that already has proper padding."""
        key = TokenManager.generate_key()
        tm = TokenManager(key)
        plaintext = '{"token": "test"}'
        encrypted = tm.encrypt(plaintext)
        decrypted = tm.decrypt(encrypted)
        assert decrypted == plaintext

    def test_key_without_proper_padding(self):
        """Test key padding normalization."""
        key = TokenManager.generate_key()
        # Remove padding and test that it still works
        if key.endswith("="):
            key_unpadded = key.rstrip("=")
        else:
            key_unpadded = key

        tm = TokenManager(key_unpadded)
        plaintext = '{"token": "test"}'
        encrypted = tm.encrypt(plaintext)
        decrypted = tm.decrypt(encrypted)
        assert decrypted == plaintext
