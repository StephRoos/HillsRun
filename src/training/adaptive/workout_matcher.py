"""Match planned workouts to completed activities (Lot D3, read-only).

Pure matching logic with no DB access, so the tolerance rules are fully
unit-testable. Each planned workout is matched to at most one activity within a
small day window (default +/-1 day) and a tolerant sport category (a planned
``road_running`` session matches a Garmin ``running``/``trail_running``
activity). Nothing here mutates the plan or the activities.
"""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel

# Planned vs actual may legitimately drift by a day (session done the evening
# before / morning after). Wider than this and we treat the session as missed.
_DEFAULT_DAY_TOLERANCE = 1


def _as_date(value: Any) -> Optional[date]:
    """Coerce a timestamp/date/ISO-string to a calendar ``date`` (or None)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None


def sport_category(
    sport_type: Optional[str], activity_type: Optional[str] = None
) -> str:
    """Map a Garmin/plan sport label to a coarse category for tolerant matching.

    Returns one of ``run``, ``bike``, ``swim``, ``strength`` or ``other``.
    """
    text = " ".join(t for t in (sport_type, activity_type) if t).lower()
    if "run" in text:
        return "run"
    if "cycl" in text or "bik" in text:
        return "bike"
    if "swim" in text:
        return "swim"
    if "strength" in text or "gym" in text or "muscle" in text:
        return "strength"
    return "other"


def _num(value: Any) -> Optional[float]:
    """Coerce a possibly-Decimal/None numeric DB value to float (or None)."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class WorkoutMatch(BaseModel):
    """One planned workout paired (or not) with a completed activity."""

    planned_id: Optional[int] = None
    planned_date: Optional[date] = None
    planned_title: Optional[str] = None
    planned_session_type: Optional[str] = None
    planned_sport_type: Optional[str] = None
    category: str = "other"

    matched: bool = False
    day_offset: Optional[int] = None  # activity_date - planned_date, in days
    activity_id: Optional[int] = None
    activity_date: Optional[date] = None
    activity_name: Optional[str] = None
    activity_sport_type: Optional[str] = None


def match_workouts(
    planned: list[dict],
    activities: list[dict],
    *,
    day_tolerance: int = _DEFAULT_DAY_TOLERANCE,
) -> list[WorkoutMatch]:
    """Greedily pair each planned workout with its nearest completed activity.

    Planned workouts are processed in date order. For each, the best unused
    activity is the one within ``day_tolerance`` days **and** the same sport
    category, minimising ``(abs(day_offset), distance_difference)``. Each
    activity is consumed by at most one planned workout.

    Args:
        planned: planned_workouts rows (need ``planned_date``, ``sport_type``;
            optional ``id``, ``title``, ``session_type``, ``target_distance_meters``).
        activities: activities rows (need ``start_timestamp``, ``sport_type``;
            optional ``activity_id``, ``activity_name``, ``activity_type``,
            ``distance_meters``).
        day_tolerance: Maximum absolute day offset accepted for a match.

    Returns:
        One ``WorkoutMatch`` per planned workout, in planned-date order.
    """
    # Pre-compute the matchable shape of each activity once.
    candidates: list[dict] = []
    for act in activities:
        act_date = _as_date(act.get("start_timestamp"))
        if act_date is None:
            continue
        candidates.append(
            {
                "row": act,
                "date": act_date,
                "category": sport_category(
                    act.get("sport_type"), act.get("activity_type")
                ),
                "distance": _num(act.get("distance_meters")),
            }
        )

    used: set[int] = set()
    ordered = sorted(planned, key=lambda p: _as_date(p.get("planned_date")) or date.max)
    matches: list[WorkoutMatch] = []

    for plan in ordered:
        plan_date = _as_date(plan.get("planned_date"))
        category = sport_category(plan.get("sport_type"), plan.get("session_type"))
        plan_distance = _num(plan.get("target_distance_meters"))

        best: Optional[tuple[float, float, int]] = None  # (|offset|, dist_diff, idx)
        for idx, cand in enumerate(candidates):
            if idx in used or plan_date is None:
                continue
            if cand["category"] != category:
                continue
            offset = abs((cand["date"] - plan_date).days)
            if offset > day_tolerance:
                continue
            if plan_distance is not None and cand["distance"] is not None:
                dist_diff = abs(cand["distance"] - plan_distance)
            else:
                dist_diff = 0.0
            key = (float(offset), dist_diff, idx)
            if best is None or key < best:
                best = key

        match = WorkoutMatch(
            planned_id=plan.get("id"),
            planned_date=plan_date,
            planned_title=plan.get("title"),
            planned_session_type=plan.get("session_type"),
            planned_sport_type=plan.get("sport_type"),
            category=category,
        )
        if best is not None:
            idx = best[2]
            used.add(idx)
            cand = candidates[idx]
            act = cand["row"]
            match.matched = True
            match.activity_id = act.get("activity_id")
            match.activity_date = cand["date"]
            match.activity_name = act.get("activity_name")
            match.activity_sport_type = act.get("sport_type")
            match.day_offset = (
                (cand["date"] - plan_date).days if plan_date is not None else None
            )
        matches.append(match)

    return matches
