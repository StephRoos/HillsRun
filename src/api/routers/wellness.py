"""Wellness endpoints."""

from fastapi import APIRouter, Depends
from ..auth import get_api_key
from ..dependencies import get_db, get_user_id, date_range, pagination
from ..schemas import HydrationData, make_page

router = APIRouter(prefix="/api/v1/wellness", tags=["wellness"], dependencies=[Depends(get_api_key)])


@router.get("/hydration")
async def hydration(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
    dates=Depends(date_range),
    pages=Depends(pagination),
):
    """Return paginated hydration data."""
    rows, total = await db.query_hydration_data(user_id, dates[0], dates[1], pages[0], pages[1])
    return make_page(rows, total, pages[0], pages[1], HydrationData)
