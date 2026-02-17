"""Sync status endpoint."""

from fastapi import APIRouter, Depends
from ..auth import get_api_key
from ..dependencies import get_db
from ..schemas import SyncStatus

router = APIRouter(prefix="/api/v1/sync", tags=["sync"], dependencies=[Depends(get_api_key)])


@router.get("/status")
async def sync_status(
    db=Depends(get_db),
):
    rows = await db.query_sync_status()
    return {"data": [SyncStatus.model_validate(dict(r)) for r in rows]}
