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
        self.key = key or os.environ.get("GARMIN_TOKEN_KEY")
        if not self.key:
            raise ValueError("GARMIN_TOKEN_KEY is required for token encryption")
        # Ensure proper base64 padding
        k = self.key if isinstance(self.key, str) else self.key.decode()
        k += "=" * (4 - len(k) % 4) if len(k) % 4 else ""
        self._fernet = Fernet(k.encode())

    def encrypt(self, token_data: str) -> bytes:
        """Encrypt token JSON string to bytes."""
        return self._fernet.encrypt(token_data.encode("utf-8"))

    def decrypt(self, encrypted: bytes) -> str:
        """Decrypt bytes back to token JSON string."""
        return self._fernet.decrypt(encrypted).decode("utf-8")

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet key."""
        return Fernet.generate_key().decode("utf-8")
