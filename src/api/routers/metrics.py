"""Advanced metrics endpoints."""

from fastapi import APIRouter, Depends
from ..auth import get_api_key
from ..dependencies import get_db, get_user_id, date_range, pagination
from ..schemas import HrvData, Spo2Data, FitnessMetrics, RespirationData, make_page

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"], dependencies=[Depends(get_api_key)])


@router.get("/hrv")
async def hrv(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
    dates=Depends(date_range),
    pages=Depends(pagination),
):
    rows, total = await db.query_hrv_data(user_id, dates[0], dates[1], pages[0], pages[1])
    return make_page(rows, total, pages[0], pages[1], HrvData)


@router.get("/spo2")
async def spo2(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
    dates=Depends(date_range),
    pages=Depends(pagination),
):
    rows, total = await db.query_spo2_data(user_id, dates[0], dates[1], pages[0], pages[1])
    return make_page(rows, total, pages[0], pages[1], Spo2Data)


@router.get("/fitness")
async def fitness(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
    dates=Depends(date_range),
    pages=Depends(pagination),
):
    rows, total = await db.query_fitness_metrics(user_id, dates[0], dates[1], pages[0], pages[1])
    return make_page(rows, total, pages[0], pages[1], FitnessMetrics)


@router.get("/respiration")
async def respiration(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
    dates=Depends(date_range),
    pages=Depends(pagination),
):
    rows, total = await db.query_respiration_data(user_id, dates[0], dates[1], pages[0], pages[1])
    return make_page(rows, total, pages[0], pages[1], RespirationData)
