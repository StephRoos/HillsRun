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
            # GarthHTTPError is a dataclass: .error holds the HTTP response object
            response = getattr(e, "error", None) or getattr(e, "response", None)
            status_code = getattr(response, "status_code", None)
            if not isinstance(status_code, int):
                status_code = None

            # Fall back to parsing the code out of the message only when the
            # structured status_code is unavailable — and parse e.msg, never
            # str(e). str(e) embeds repr(self.error), whose stray digits (mock
            # ids in tests, content-length/timestamps in prod) would otherwise
            # misclassify the error (e.g. a 401 read as 400).
            if status_code is None:
                raw_msg = getattr(e, "msg", "")
                msg_text = raw_msg if isinstance(raw_msg, str) else ""
                for code in (400, 401, 403, 404, 429, 500, 503):
                    if str(code) in msg_text:
                        status_code = code
                        break

            messages = {
                400: "Endpoint not available (400) - Feature may not be enabled",
                401: "Authentication required (401) - Please re-authenticate",
                403: "Access denied (403) - No permission",
                404: "Endpoint not found (404) - Feature may be removed",
                429: "Rate limit exceeded (429) - Wait before retrying",
                500: "Server error (500) - Garmin servers issue",
                503: "Service unavailable (503) - Temporary outage",
            }
            msg = messages.get(status_code, f"HTTP error ({status_code}): {error_str}")

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
