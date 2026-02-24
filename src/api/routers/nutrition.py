"""Nutrition endpoints for RecettesApp integration."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Response

from ..auth import get_api_key
from ..dependencies import get_db, get_user_id
from ..schemas import NutritionDailyGoal, TrainingLoad

router = APIRouter(
    prefix="/api/v1/nutrition", tags=["nutrition"], dependencies=[Depends(get_api_key)]
)

_RECOVERY_MARGIN = 1.1


@router.get("/daily-goal", response_model=NutritionDailyGoal)
async def get_daily_calorie_goal(
    target_date: date = Query(default_factory=date.today, alias="date"),
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Return recommended daily calorie intake for a given date.

    Combines base metabolic rate (BMR) and active calories from Garmin's
    daily summary with a 10% recovery margin on active calories. Also
    returns training load details from the primary activity of the day.

    Args:
        target_date: Date to compute the goal for (defaults to today).
        db: Database dependency.
        user_id: Resolved Garmin user ID.

    Returns:
        NutritionDailyGoal with calorie breakdown and training load.
        Returns HTTP 204 when no Garmin data is available for the date.
    """
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
