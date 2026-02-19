"""FastAPI application for HillsRun API."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..config import DatabaseConfig
from ..database import Database
from .routers import health, daily, body, metrics, activities, wellness, sync, auth_garmin, planned_workouts, coaching

logger = logging.getLogger(__name__)


def _db_config_from_env() -> DatabaseConfig:
    return DatabaseConfig(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ.get("POSTGRES_DB", "garmin_connect"),
        user=os.environ.get("POSTGRES_USER", "garmin"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database(_db_config_from_env())
    await db.connect()
    app.state.db = db
    app.state.user_id = await db.query_first_user()
    logger.info(f"API started, user_id={app.state.user_id}")
    yield
    await db.disconnect()


app = FastAPI(
    title="HillsRun API",
    description="REST API for Garmin Connect data stored in PostgreSQL",
    version="1.0.0",
    lifespan=lifespan,
)

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
