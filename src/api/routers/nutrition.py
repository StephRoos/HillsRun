"""Nutrition endpoints for RecettesApp integration."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..auth import get_api_key
from ..dependencies import get_db
from ..schemas import NutritionDailyGoal, TrainingLoad

router = APIRouter(
    prefix="/api/v1/nutrition", tags=["nutrition"], dependencies=[Depends(get_api_key)]
)

# Per-user rate limit: 100 requests/day (daily goal rarely changes)
_nutrition_limiter = Limiter(key_func=get_remote_address)
_NUTRITION_RATE_LIMIT = "100/day"

_RECOVERY_MARGIN = 1.1


def _get_better_auth_id(request: Request) -> str:
    """Extract X-Better-Auth-User-Id header, raising 401 if missing.

    This endpoint is designed for cross-service calls from RecettesApp,
    which identifies users via their Better-Auth user ID.
    """
    value = request.headers.get("X-Better-Auth-User-Id")
    if not value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Better-Auth-User-Id header required",
        )
    return value


@router.get("/daily-goal", response_model=NutritionDailyGoal)
@_nutrition_limiter.limit(_NUTRITION_RATE_LIMIT)
async def get_daily_calorie_goal(
    request: Request,
    target_date: date = Query(default_factory=date.today, alias="date"),
    db=Depends(get_db),
    better_auth_id: str = Depends(_get_better_auth_id),
):
    """Return recommended daily calorie intake for a given date.

    Combines base metabolic rate (BMR) and active calories from Garmin's
    daily summary with a 10% recovery margin on active calories. Also
    returns training load details from the primary activity of the day.

    Auth: X-API-Key + X-Better-Auth-User-Id (cross-service from RecettesApp).

    Args:
        request: FastAPI request (needed for rate limiting).
        target_date: Date to compute the goal for (defaults to today).
        db: Database dependency.
        better_auth_id: Better-Auth user ID from header.

    Returns:
        NutritionDailyGoal with calorie breakdown and training load.
        HTTP 204 when no Garmin data is available for the date.
        HTTP 404 when no Garmin account is linked to this Better-Auth user.
    """
    # Resolve Better-Auth user ID → Garmin user_id
    user_id = await db.get_user_by_better_auth_id(better_auth_id)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Garmin account linked to this user",
        )

    data = await db.query_nutrition_goal(user_id, target_date)
    if data is None:
        return Response(status_code=204)

    bmr = data.get("bmr_calories")
    active = data.get("active_calories")

    recommended: int | None = None
    adjustment_factor: float | None = None
    total_training_calories: int | None = None

    if bmr is not None and active is not None:
        adjustment_factor = _RECOVERY_MARGIN
        total_training_calories = int(active * adjustment_factor)
        recommended = bmr + total_training_calories
    elif bmr is not None:
        recommended = bmr

    training_load: TrainingLoad | None = None
    activity_type = data.get("activity_type")
    duration_seconds = data.get("duration_seconds")
    tss = data.get("training_stress_score")

    if activity_type or duration_seconds or tss:
        duration_minutes: int | None = (
            int(duration_seconds / 60) if duration_seconds is not None else None
        )
        training_load = TrainingLoad(
            tss=tss,
            duration_minutes=duration_minutes,
            activity_type=activity_type,
        )

    return NutritionDailyGoal(
        date=target_date,
        base_bmr_calories=bmr,
        active_calories=active,
        total_training_calories=total_training_calories,
        recommended_daily_intake=recommended,
        training_load=training_load,
        adjustment_factor=adjustment_factor,
    )
