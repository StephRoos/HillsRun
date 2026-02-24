"""Planned workouts endpoints."""

import csv
import io
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status
from fastapi.responses import StreamingResponse
from ..auth import get_api_key
from ..dependencies import (
    get_db,
    get_user_id,
    date_range,
    pagination,
    verify_coach_access,
)
from ..schemas import (
    PlannedWorkout,
    PlannedWorkoutCreate,
    PlannedWorkoutUpdate,
    BulkImportResult,
    VALID_SPORT_TYPES,
    VALID_INTENSITIES,
    make_page,
)

router = APIRouter(
    prefix="/api/v1/planned-workouts",
    tags=["planned-workouts"],
    dependencies=[Depends(get_api_key)],
)


def _validate_sport_type(sport_type: str) -> None:
    """Raise 422 if sport_type is not in VALID_SPORT_TYPES."""
    if sport_type not in VALID_SPORT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sport_type '{sport_type}'. Allowed: {sorted(VALID_SPORT_TYPES)}",
        )


def _validate_intensity(intensity: str) -> None:
    """Raise 422 if intensity is not in VALID_INTENSITIES."""
    if intensity not in VALID_INTENSITIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid intensity '{intensity}'. Allowed: {sorted(VALID_INTENSITIES)}",
        )


@router.get("")
async def list_planned_workouts(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
    dates=Depends(date_range),
    pages=Depends(pagination),
):
    """Return paginated planned workouts for a date range."""
    rows, total = await db.query_planned_workouts(
        user_id, dates[0], dates[1], pages[0], pages[1]
    )
    return make_page(rows, total, pages[0], pages[1], PlannedWorkout)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_planned_workout(
    body: PlannedWorkoutCreate,
    request: Request,
    db=Depends(get_db),
):
    """Create a new planned workout. Coaches can create for their athletes."""
    _validate_sport_type(body.sport_type)
    _validate_intensity(body.intensity)
    user_id, coach_id = await verify_coach_access(request)
    data = body.model_dump()
    if coach_id:
        data["created_by_user_id"] = coach_id
    row = await db.create_planned_workout(user_id, data)
    return PlannedWorkout.model_validate(row)


@router.get("/template")
async def download_template():
    """Download a CSV template for bulk workout import."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "date",
            "sport_type",
            "title",
            "description",
            "duration_minutes",
            "distance_km",
            "intensity",
        ]
    )
    writer.writerow(["2026-03-01", "running", "Easy run", "", "45", "10", "easy"])
    writer.writerow(
        [
            "2026-03-02",
            "strength_training",
            "Upper body",
            "Gym session",
            "60",
            "",
            "moderate",
        ]
    )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=planned_workouts_template.csv"
        },
    )


@router.post("/import")
async def import_planned_workouts(
    request: Request,
    file: UploadFile = File(...),
    db=Depends(get_db),
):
    """Import planned workouts from a CSV file (max 1 MB)."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    MAX_SIZE = 1 * 1024 * 1024  # 1 MB
    content = await file.read(MAX_SIZE + 1)
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 1 MB)")
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    workouts = []
    errors = []

    for i, row in enumerate(reader, start=2):  # row 1 is header
        try:
            sport_type = row.get("sport_type", "").strip()
            if sport_type not in VALID_SPORT_TYPES:
                errors.append(f"Row {i}: invalid sport_type '{sport_type}'")
                continue

            intensity = row.get("intensity", "moderate").strip() or "moderate"
            if intensity not in VALID_INTENSITIES:
                errors.append(f"Row {i}: invalid intensity '{intensity}'")
                continue

            title = row.get("title", "").strip()
            if not title:
                errors.append(f"Row {i}: title is required")
                continue

            planned_date = date.fromisoformat(row["date"].strip())

            duration_str = row.get("duration_minutes", "").strip()
            duration_seconds = int(float(duration_str) * 60) if duration_str else None

            distance_str = row.get("distance_km", "").strip()
            distance_meters = float(distance_str) * 1000 if distance_str else None

            workouts.append(
                {
                    "planned_date": planned_date,
                    "sport_type": sport_type,
                    "title": title,
                    "description": row.get("description", "").strip() or None,
                    "planned_duration_seconds": duration_seconds,
                    "planned_distance_meters": distance_meters,
                    "intensity": intensity,
                }
            )
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    user_id, coach_id = await verify_coach_access(request)
    imported = await db.bulk_create_planned_workouts(
        user_id, workouts, created_by_user_id=coach_id
    )
    return BulkImportResult(imported=imported, errors=errors)


@router.get("/{workout_id}")
async def get_planned_workout(
    workout_id: int,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Return a single planned workout by ID.

    Raises:
        HTTPException: 404 if not found.
    """
    row = await db.get_planned_workout(workout_id, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Planned workout not found")
    return PlannedWorkout.model_validate(row)


@router.patch("/{workout_id}")
async def update_planned_workout(
    workout_id: int,
    body: PlannedWorkoutUpdate,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Update a planned workout by ID.

    Raises:
        HTTPException: 404 if not found.
    """
    if body.sport_type is not None:
        _validate_sport_type(body.sport_type)
    if body.intensity is not None:
        _validate_intensity(body.intensity)

    row = await db.update_planned_workout(
        workout_id, user_id, body.model_dump(exclude_unset=True)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Planned workout not found")
    return PlannedWorkout.model_validate(row)


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_planned_workout(
    workout_id: int,
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Delete a planned workout by ID.

    Raises:
        HTTPException: 404 if not found.
    """
    deleted = await db.delete_planned_workout(workout_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Planned workout not found")
