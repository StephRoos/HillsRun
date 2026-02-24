"""Health check endpoint."""

from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..schemas import HealthResponse
from ...version import __version__

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health(request: Request):
    """Health check endpoint for monitoring and deploy verification.

    Returns app status, version, uptime and DB connectivity.
    No authentication required — safe for load balancers and external monitors.

    Returns:
        HealthResponse with status "ok" if DB is reachable, "degraded" (503) otherwise.
    """
    db = request.app.state.db
    start_time: datetime | None = getattr(request.app.state, "start_time", None)

    uptime_seconds: float | None = None
    if start_time is not None:
        uptime_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()

    try:
        await db.pool.fetchval("SELECT 1")
        return HealthResponse(
            status="ok",
            version=__version__,
            uptime_seconds=uptime_seconds,
            db_connected=True,
        )
    except Exception:
        return JSONResponse(
            content=HealthResponse(
                status="degraded",
                version=__version__,
                uptime_seconds=uptime_seconds,
                db_connected=False,
            ).model_dump(),
            status_code=503,
        )
