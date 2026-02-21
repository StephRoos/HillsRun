"""User profile endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth import get_api_key
from ..dependencies import get_db, get_user_id

router = APIRouter(prefix="/api/v1/user", tags=["user"], dependencies=[Depends(get_api_key)])


class VmaResponse(BaseModel):
    """VMA data response."""
    manual_vma: Optional[float] = None
    estimated_vma: Optional[float] = None


class VmaUpdate(BaseModel):
    """Request body for updating manual VMA."""
    vma: Optional[float] = Field(None, ge=5, le=30, description="VMA in km/h, or null to clear")


@router.get("/vma")
async def get_vma(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> VmaResponse:
    """Return manual and estimated VMA for a user."""
    manual_vma = await db.get_user_vma(user_id)
    vo2max = await db.get_latest_vo2max_running(user_id)
    estimated_vma = round(float(vo2max) / 3.5, 2) if vo2max else None
    return VmaResponse(manual_vma=float(manual_vma) if manual_vma else None, estimated_vma=estimated_vma)


@router.patch("/vma")
async def update_vma(
    body: VmaUpdate,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> VmaResponse:
    """Update manual VMA for a user. Send null to clear."""
    await db.update_user_vma(user_id, body.vma)
    vo2max = await db.get_latest_vo2max_running(user_id)
    estimated_vma = round(float(vo2max) / 3.5, 2) if vo2max else None
    return VmaResponse(manual_vma=body.vma, estimated_vma=estimated_vma)
