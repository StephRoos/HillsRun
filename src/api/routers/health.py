"""Health check endpoint."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from ..schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health(request: Request):
    """Health check: verify DB connectivity.

    Returns:
        {"status": "ok"} if DB is reachable, {"status": "degraded"} (503) otherwise.
    """
    db = request.app.state.db
    try:
        await db.pool.fetchval("SELECT 1")
        return {"status": "ok"}
    except Exception:
        return JSONResponse({"status": "degraded"}, status_code=503)
