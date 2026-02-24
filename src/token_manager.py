"""Garmin token encryption/decryption using Fernet (symmetric AES)."""

import json
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages encryption and decryption of Garmin OAuth tokens."""

    def __init__(self, key: Optional[str] = None):
        """Initialize TokenManager with a Fernet encryption key.

        Args:
            key: Fernet key string. Falls back to GARMIN_TOKEN_KEY env var.

        Raises:
            ValueError: If no key is provided or found in environment.
        """
        self.key = key or os.environ.get("GARMIN_TOKEN_KEY")
        if not self.key:
            raise ValueError("GARMIN_TOKEN_KEY is required for token encryption")
        # Ensure proper base64 padding
        k = self.key if isinstance(self.key, str) else self.key.decode()
        k += "=" * (4 - len(k) % 4) if len(k) % 4 else ""
        self._fernet = Fernet(k.encode())

    def encrypt(self, token_data: str) -> bytes:
        """Encrypt a token JSON string.

        Args:
            token_data: JSON string of Garmin OAuth tokens.

        Returns:
            Encrypted bytes.
        """
        return self._fernet.encrypt(token_data.encode("utf-8"))

    def decrypt(self, encrypted: bytes) -> str:
        """Decrypt encrypted token bytes back to a JSON string.

        Args:
            encrypted: Fernet-encrypted bytes.

        Returns:
            Decrypted JSON string.

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails.
        """
        return self._fernet.decrypt(encrypted).decode("utf-8")

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet encryption key.

        Returns:
            URL-safe base64-encoded key string.
        """
        return Fernet.generate_key().decode("utf-8")
