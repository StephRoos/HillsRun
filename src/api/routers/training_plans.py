"""Training plans API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_api_key
from ..dependencies import get_db, get_user_id, pagination
from ..schemas import (
    AthleteProfileCreate,
    AthleteProfileResponse,
    FitnessSnapshotResponse,
    GeneratePlanRequestSchema,
    PlanWeekDetail,
    RaceTargetCreate,
    RaceTargetResponse,
    TrainingPlanDetail,
    TrainingPlanStatusUpdate,
    TrainingPlanSummary,
    make_page,
)
from ...training import db_operations as db_ops
from ...training.fitness_snapshot import build_fitness_snapshot
from ...training.models import GeneratePlanRequest
from ...training.plan_generator import generate_plan

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/training-plans",
    tags=["training-plans"],
    dependencies=[Depends(get_api_key)],
)


# ============================================
# Static routes FIRST (before /{plan_id})
# ============================================


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_training_plan(
    body: GeneratePlanRequestSchema,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Generate a complete training plan for a race target."""
    request = GeneratePlanRequest(
        race_target_id=body.race_target_id,
        plan_name=body.plan_name,
        total_weeks=body.total_weeks,
        start_date=body.start_date,
    )
    try:
        result = await generate_plan(db.pool, user_id, request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Plan generation failed for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plan generation error: {e}",
        )
    return result


@router.get("/profile")
async def get_athlete_profile(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Get athlete profile."""
    profile = await db_ops.get_athlete_profile(db.pool, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Athlete profile not found")
    return AthleteProfileResponse.model_validate(profile)


@router.put("/profile")
async def upsert_athlete_profile(
    body: AthleteProfileCreate,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Create or update athlete profile."""
    profile = await db_ops.upsert_athlete_profile(db.pool, user_id, body.model_dump())
    return AthleteProfileResponse.model_validate(profile)


@router.post("/races", status_code=status.HTTP_201_CREATED)
async def create_race_target(
    body: RaceTargetCreate,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Create a new race target."""
    race = await db_ops.create_race_target(db.pool, user_id, body.model_dump())
    return RaceTargetResponse.model_validate(race)


@router.get("/races")
async def list_race_targets(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """List all race targets for the user."""
    rows = await db_ops.list_race_targets(db.pool, user_id)
    return rows


@router.delete("/races/{race_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_race_target(
    race_id: int,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Delete a race target."""
    deleted = await db_ops.delete_race_target(db.pool, race_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Race target not found")


@router.get("/fitness-snapshot")
async def get_fitness_snapshot(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Get current fitness data snapshot for plan generation."""
    snapshot = await build_fitness_snapshot(db.pool, user_id)
    return FitnessSnapshotResponse.model_validate(snapshot.model_dump())


# ============================================
# Dynamic routes with {plan_id}
# ============================================


@router.get("")
async def list_training_plans(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
    pages=Depends(pagination),
):
    """List training plans for the user (paginated)."""
    rows, total = await db_ops.list_training_plans(db.pool, user_id, pages[0], pages[1])
    return make_page(rows, total, pages[0], pages[1], TrainingPlanSummary)


@router.get("/{plan_id}")
async def get_training_plan(
    plan_id: int,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Get training plan detail with all weeks."""
    plan = await db_ops.get_training_plan(db.pool, plan_id, user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Training plan not found")

    weeks = await db_ops.get_plan_weeks(db.pool, plan_id)
    plan["weeks"] = weeks
    return TrainingPlanDetail.model_validate(plan)


@router.patch("/{plan_id}")
async def update_training_plan_status(
    plan_id: int,
    body: TrainingPlanStatusUpdate,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Update training plan status (active, cancelled, completed)."""
    valid_statuses = {"active", "cancelled", "completed"}
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Allowed: {sorted(valid_statuses)}",
        )
    plan = await db_ops.update_training_plan_status(db.pool, plan_id, user_id, body.status)
    if not plan:
        raise HTTPException(status_code=404, detail="Training plan not found")
    return TrainingPlanSummary.model_validate(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training_plan(
    plan_id: int,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Delete a training plan (cascades to weeks and sessions)."""
    deleted = await db_ops.delete_training_plan(db.pool, plan_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Training plan not found")


@router.get("/{plan_id}/weeks/{week_number}")
async def get_plan_week(
    plan_id: int,
    week_number: int,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Get a specific week with all sessions."""
    plan = await db_ops.get_training_plan(db.pool, plan_id, user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Training plan not found")

    week = await db_ops.get_plan_week_by_number(db.pool, plan_id, week_number)
    if not week:
        raise HTTPException(status_code=404, detail="Week not found")

    sessions = await db_ops.get_plan_sessions_for_week(db.pool, week["id"])
    week["sessions"] = sessions
    return PlanWeekDetail.model_validate(week)
