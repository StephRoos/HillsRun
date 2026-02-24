"""Cache-Control middleware for HillsRun API.

Adds appropriate Cache-Control headers to GET responses based on
the requested date range:
- Historical data (end_date < today): public, max-age=86400 (24h)
- Current data (end_date == today or no date): private, max-age=300 (5 min)
- Non-cacheable endpoints (sync, auth, coaching, nutrition): no-store
"""

from datetime import date
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Prefixes that must never be cached
_NO_CACHE_PREFIXES = (
    "/api/v1/sync",
    "/api/v1/auth",
    "/api/v1/coaching",
    "/api/v1/nutrition",
)

# Prefixes that support date-range caching
_CACHEABLE_PREFIXES = (
    "/api/v1/daily",
    "/api/v1/body",
    "/api/v1/metrics",
    "/api/v1/activities",
)

_MAX_AGE_HISTORICAL = 86400  # 24 hours — historical data never changes
_MAX_AGE_CURRENT = 300  # 5 minutes — data may still be updated today


def _is_no_cache_path(path: str) -> bool:
    """Return True if the path should never be cached."""
    return any(path.startswith(prefix) for prefix in _NO_CACHE_PREFIXES)


def _is_cacheable_path(path: str) -> bool:
    """Return True if the path supports date-range caching."""
    return any(path.startswith(prefix) for prefix in _CACHEABLE_PREFIXES)


def _resolve_cache_control(end_date_param: str | None) -> str:
    """Compute the Cache-Control header value given an end_date query parameter.

    Args:
        end_date_param: The raw ``end_date`` query string value, or None when
            the parameter is absent.

    Returns:
        A Cache-Control header value string.
    """
    today = date.today()

    if end_date_param:
        try:
            end = date.fromisoformat(end_date_param)
            if end < today:
                return f"public, max-age={_MAX_AGE_HISTORICAL}"
        except ValueError:
            pass

    # No date param, today, or unparseable value → treat as current data
    return f"private, max-age={_MAX_AGE_CURRENT}"


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Middleware that sets Cache-Control headers on GET responses.

    Rules:
    - Sync / auth / coaching / nutrition endpoints: ``Cache-Control: no-store``
    - Cacheable endpoints with ``end_date`` strictly before today:
      ``Cache-Control: public, max-age=86400``
    - Cacheable endpoints with ``end_date`` == today or absent:
      ``Cache-Control: private, max-age=300``
    - All other paths: no header added.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and inject Cache-Control on eligible responses.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware / route handler.

        Returns:
            HTTP response with Cache-Control header when applicable.
        """
        response: Response = await call_next(request)

        # Only apply to GET requests
        if request.method != "GET":
            return response

        path = request.url.path

        if _is_no_cache_path(path):
            response.headers["Cache-Control"] = "no-store"
            return response

        if _is_cacheable_path(path):
            end_date_param = request.query_params.get("end_date")
            header_value = _resolve_cache_control(end_date_param)
            response.headers["Cache-Control"] = header_value

        return response
