"""Daily health data endpoints."""

from fastapi import APIRouter, Depends
from ..auth import get_api_key
from ..dependencies import get_db, get_user_id, date_range, pagination
from ..schemas import (
    DailySummary,
    HeartRateSample,
    SleepData,
    StressData,
    BodyBattery,
    make_page,
)

router = APIRouter(
    prefix="/api/v1/daily", tags=["daily"], dependencies=[Depends(get_api_key)]
)


@router.get("/summary")
async def daily_summary(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
    dates=Depends(date_range),
    pages=Depends(pagination),
):
    """Return paginated daily health summaries."""
    rows, total = await db.query_daily_summaries(
        user_id, dates[0], dates[1], pages[0], pages[1]
    )
    return make_page(rows, total, pages[0], pages[1], DailySummary)


@router.get("/heart-rate")
async def heart_rate(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
    dates=Depends(date_range),
    pages=Depends(pagination),
):
    """Return paginated heart rate samples (max 5000 per page)."""
    limit = min(pages[0], 5000)
    rows, total = await db.query_heart_rate_samples(
        user_id, dates[0], dates[1], limit, pages[1]
    )
    return make_page(rows, total, limit, pages[1], HeartRateSample)


@router.get("/sleep")
async def sleep(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
    dates=Depends(date_range),
    pages=Depends(pagination),
):
    """Return paginated sleep data."""
    rows, total = await db.query_sleep_data(
        user_id, dates[0], dates[1], pages[0], pages[1]
    )
    return make_page(rows, total, pages[0], pages[1], SleepData)


@router.get("/stress")
async def stress(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
    dates=Depends(date_range),
    pages=Depends(pagination),
):
    """Return paginated stress data."""
    rows, total = await db.query_stress_data(
        user_id, dates[0], dates[1], pages[0], pages[1]
    )
    return make_page(rows, total, pages[0], pages[1], StressData)


@router.get("/body-battery")
async def body_battery(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
    dates=Depends(date_range),
    pages=Depends(pagination),
):
    """Return paginated body battery data."""
    rows, total = await db.query_body_battery(
        user_id, dates[0], dates[1], pages[0], pages[1]
    )
    return make_page(rows, total, pages[0], pages[1], BodyBattery)
