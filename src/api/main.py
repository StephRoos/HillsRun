"""FastAPI application for HillsRun API."""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from ..config import DatabaseConfig
from ..database import Database
from .middleware import CacheControlMiddleware
from .routers import (
    health,
    daily,
    body,
    metrics,
    activities,
    wellness,
    sync,
    auth_garmin,
    planned_workouts,
    coaching,
    user,
    nutrition,
)

logger = logging.getLogger(__name__)


def _db_config_from_env() -> DatabaseConfig:
    """Build DatabaseConfig from environment variables."""
    return DatabaseConfig(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ.get("POSTGRES_DB", "garmin_connect"),
        user=os.environ.get("POSTGRES_USER", "garmin"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
    )


def _validate_token_key():
    """Validate GARMIN_TOKEN_KEY env var at startup.

    Raises:
        RuntimeError: If key is not set or not a valid Fernet key.
    """
    from cryptography.fernet import Fernet

    key = os.environ.get("GARMIN_TOKEN_KEY", "")
    if not key:
        raise RuntimeError("GARMIN_TOKEN_KEY environment variable is not set")
    try:
        # Add base64 padding if needed (matches token_manager.py behavior)
        k = key if isinstance(key, str) else key.decode()
        k += "=" * (4 - len(k) % 4) if len(k) % 4 else ""
        Fernet(k.encode())
    except Exception as exc:
        raise RuntimeError(f"GARMIN_TOKEN_KEY is not a valid Fernet key: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: configure logging, validate keys, connect DB."""
    from ..utils.logging_config import setup_logging

    setup_logging(log_level=os.environ.get("LOG_LEVEL", "INFO"))
    _validate_token_key()
    db = Database(_db_config_from_env())
    await db.connect()
    app.state.db = db
    app.state.user_id = await db.query_first_user()
    app.state.start_time = datetime.now(timezone.utc)
    logger.info(f"API started, user_id={app.state.user_id}")
    yield
    await db.disconnect()


app = FastAPI(
    title="HillsRun API",
    description="REST API for Garmin Connect data stored in PostgreSQL",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CacheControlMiddleware)

app.include_router(health.router)
app.include_router(daily.router)
app.include_router(body.router)
app.include_router(metrics.router)
app.include_router(activities.router)
app.include_router(wellness.router)
app.include_router(sync.router)
app.include_router(auth_garmin.router)
app.include_router(planned_workouts.router)
app.include_router(coaching.router)
app.include_router(user.router)
app.include_router(nutrition.router)
