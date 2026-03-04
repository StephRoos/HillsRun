"""Rate limiting configuration for HillsRun API.

Uses slowapi to enforce per-IP rate limits:
- Global: 100 requests/minute for all endpoints
- Auth endpoints: 5 requests/15 minutes (brute-force protection)
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiter instance — key_func extracts client IP from the request
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# Stricter limits for auth endpoints (brute-force protection)
AUTH_RATE_LIMIT = "5/15minutes"
