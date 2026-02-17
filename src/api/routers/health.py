"""Health check endpoint."""

from fastapi import APIRouter, Request
from ..schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health(request: Request):
    db = request.app.state.db
    try:
        await db.pool.fetchval("SELECT 1")
        return {"status": "ok"}
    except Exception:
        return {"status": "degraded"}
