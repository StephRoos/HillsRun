"""Retry utilities with exponential backoff."""

import logging
from functools import wraps
from typing import Callable, Type, Tuple

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)
from garminconnect import (
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)
from garth.exc import GarthHTTPError

logger = logging.getLogger(__name__)


# Define retryable exceptions
RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    ConnectionError,
    TimeoutError,
)


def create_retry_decorator(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 10,
    exceptions: Tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS,
):
    """Create a retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Tuple of exception types to retry on

    Returns:
        Configured retry decorator
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


# Default retry decorator for API calls
retry_api_call = create_retry_decorator(
    max_attempts=3,
    min_wait=2,
    max_wait=30,
)


def safe_api_call(func: Callable) -> Callable:
    """Decorator to safely execute API calls with error handling.

    Catches exceptions and returns (success, result, error_message) tuple.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function that returns (bool, Any, Optional[str])
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return True, result, None
        except GarthHTTPError as e:
            error_str = str(e)
            status_code = getattr(getattr(e, "response", None), "status_code", None)

            if status_code == 400 or "400" in error_str:
                msg = "Endpoint not available (400) - Feature may not be enabled"
            elif status_code == 401 or "401" in error_str:
                msg = "Authentication required (401) - Please re-authenticate"
            elif status_code == 403 or "403" in error_str:
                msg = "Access denied (403) - No permission"
            elif status_code == 404 or "404" in error_str:
                msg = "Endpoint not found (404) - Feature may be removed"
            elif status_code == 429 or "429" in error_str:
                msg = "Rate limit exceeded (429) - Wait before retrying"
            elif status_code == 500 or "500" in error_str:
                msg = "Server error (500) - Garmin servers issue"
            elif status_code == 503 or "503" in error_str:
                msg = "Service unavailable (503) - Temporary outage"
            else:
                msg = f"HTTP error ({status_code}): {error_str}"

            logger.warning(f"API call failed: {msg}")
            return False, None, msg

        except GarminConnectTooManyRequestsError as e:
            msg = f"Rate limit exceeded: {e}"
            logger.warning(msg)
            return False, None, msg

        except GarminConnectConnectionError as e:
            msg = f"Connection error: {e}"
            logger.error(msg)
            return False, None, msg

        except RetryError as e:
            msg = f"Max retries exceeded: {e}"
            logger.error(msg)
            return False, None, msg

        except Exception as e:
            msg = f"Unexpected error: {type(e).__name__}: {e}"
            logger.exception(msg)
            return False, None, msg

    return wrapper
