"""Adaptive coach API endpoints (Chantier D).

Read-only daily readiness based on morning HRV versus an individual baseline.
This router never mutates the training plan — it returns (and records) a verdict
plus a suggested, non-applied session modification.
"""

import logging
from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..auth import get_api_key
from ..dependencies import get_db, get_user_id
from ...training.adaptive.queries import evaluate_daily_readiness

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/training",
    tags=["adaptive-coach"],
    dependencies=[Depends(get_api_key)],
)


@router.get("/daily-readiness")
async def get_daily_readiness(
    date: Optional[date_type] = Query(
        default=None, description="Day to evaluate (default: today)"
    ),
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Return today's HRV-baseline readiness verdict (does NOT mutate the plan).

    The verdict is GREEN (proceed), AMBER (ease the session), RED (rest /
    active recovery) or ``insufficient_baseline`` when fewer than 28 daily HRV
    points exist. The suggested modification is advisory only.
    """
    day = date or date_type.today()
    result = await evaluate_daily_readiness(db.pool, user_id, day)
    return {
        "date": day.isoformat(),
        "verdict": result.verdict.value,
        "reason": result.reason,
        "suggested_modification": result.suggested_modification,
        "hrv_value": result.hrv_value,
        "baseline_low": result.baseline_low,
        "baseline_high": result.baseline_high,
    }
