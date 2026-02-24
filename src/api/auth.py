"""API Key authentication dependency."""

import hmac
import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Validate the X-API-Key header against the configured API_KEY.

    Args:
        api_key: API key from request header.

    Returns:
        The validated API key string.

    Raises:
        HTTPException: If key is missing, invalid, or not configured.
    """
    expected = os.environ.get("API_KEY", "")
    if not expected:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="API key not configured")
    if not api_key or not hmac.compare_digest(api_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
    return api_key
