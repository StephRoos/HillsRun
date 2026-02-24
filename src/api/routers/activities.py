"""Activities endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from ..auth import get_api_key
from ..dependencies import get_db, get_user_id, date_range, pagination
from ..schemas import Activity, ActivityDetail, ActivitySplit, ActivityUpdate, make_page

router = APIRouter(prefix="/api/v1/activities", tags=["activities"], dependencies=[Depends(get_api_key)])


@router.get("")
async def list_activities(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
    dates=Depends(date_range),
    pages=Depends(pagination),
    sport_type: Optional[str] = Query(default=None),
    activity_type: Optional[str] = Query(default=None),
):
    """Return paginated activities, optionally filtered by sport/activity type."""
    rows, total = await db.query_activities(
        user_id, dates[0], dates[1], pages[0], pages[1], sport_type, activity_type
    )
    return make_page(rows, total, pages[0], pages[1], Activity)


@router.get("/{activity_id}")
async def get_activity(
    activity_id: int,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Return full detail for a single activity.

    Raises:
        HTTPException: 404 if activity not found.
    """
    row = await db.query_activity_by_id(activity_id, user_id=user_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    return ActivityDetail.model_validate(dict(row))


@router.patch("/{activity_id}")
async def update_activity(
    activity_id: int,
    body: ActivityUpdate,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Update an activity's custom_name.

    Raises:
        HTTPException: 404 if activity not found.
    """
    updated = await db.update_activity_custom_name(activity_id, body.custom_name, user_id=user_id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    row = await db.query_activity_by_id(activity_id, user_id=user_id)
    return ActivityDetail.model_validate(dict(row))


@router.get("/{activity_id}/splits")
async def get_activity_splits(
    activity_id: int,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Return splits/laps for a single activity."""
    rows = await db.query_activity_splits(activity_id, user_id=user_id)
    return {"data": [ActivitySplit.model_validate(dict(r)) for r in rows]}
