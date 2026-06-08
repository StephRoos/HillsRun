"""Plan-vs-actual adherence (Lot D3, read-only).

Turns the planned/actual pairs from ``workout_matcher`` into per-session and
per-week compliance figures: completed?, actual versus planned
duration/distance/pace, and realized weekly TSS. Everything is a pure function
of its inputs (no DB) so the compliance maths is fully unit-testable.

ACWR is exposed under ``acwr_informational`` with an explicit contested note —
it is **never** used to gate a decision (spec 03 §0/§3).
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel

from .workout_matcher import WorkoutMatch, _as_date, _num

# ACWR has no validated safe range; surfaced for context only, never as a rule.
ACWR_CONTESTED_NOTE = (
    "ACWR is contested (no validated safe range, and anti-ACWR claims are also "
    "refuted) — shown for information only, never used to adjust the plan."
)

_METERS_PER_KM = 1000.0


def _pace_sec_per_km(
    duration_seconds: Optional[float], distance_meters: Optional[float]
) -> Optional[float]:
    """Derive pace in seconds per km, or None when inputs are unusable."""
    if not duration_seconds or not distance_meters or distance_meters <= 0:
        return None
    return duration_seconds / (distance_meters / _METERS_PER_KM)


def _ratio(actual: Optional[float], planned: Optional[float]) -> Optional[float]:
    """Actual-over-planned ratio, or None when planned is missing/zero."""
    if actual is None or not planned:
        return None
    return actual / planned


class SessionAdherence(BaseModel):
    """Planned vs actual for a single session."""

    planned_id: Optional[int] = None
    session_date: Optional[date] = None
    session_type: Optional[str] = None
    sport_type: Optional[str] = None
    title: Optional[str] = None

    completed: bool = False
    activity_id: Optional[int] = None
    day_offset: Optional[int] = None

    planned_duration_seconds: Optional[float] = None
    actual_duration_seconds: Optional[float] = None
    planned_distance_meters: Optional[float] = None
    actual_distance_meters: Optional[float] = None
    planned_pace_sec_per_km: Optional[float] = None
    actual_pace_sec_per_km: Optional[float] = None
    planned_tss: Optional[float] = None
    actual_tss: Optional[float] = None

    duration_ratio: Optional[float] = None
    distance_ratio: Optional[float] = None


class WeekAdherence(BaseModel):
    """Aggregated compliance for a single plan week (read-only report)."""

    week_number: Optional[int] = None
    planned_sessions: int = 0
    completed_sessions: int = 0
    compliance_pct: float = 0.0
    planned_tss: float = 0.0
    realized_tss: float = 0.0
    sessions: list[SessionAdherence] = []
    acwr_informational: Optional[dict] = None


def build_session_adherence(
    match: WorkoutMatch,
    planned_row: dict,
    activity_row: Optional[dict],
) -> SessionAdherence:
    """Per-session adherence from a match plus its planned + activity rows.

    Folds the planned targets and the actual results into one comparison with
    duration/distance ratios. ``activity_row`` is ``None`` for a missed session.

    Args:
        match: The planned/actual pairing from ``match_workouts``.
        planned_row: The planned_workouts row (planned targets).
        activity_row: The matched activities row, or ``None`` if missed.

    Returns:
        A populated ``SessionAdherence``.
    """
    out = SessionAdherence(
        planned_id=match.planned_id,
        session_date=match.planned_date,
        session_type=match.planned_session_type,
        sport_type=match.planned_sport_type,
        title=match.planned_title,
        completed=match.matched,
        activity_id=match.activity_id,
        day_offset=match.day_offset,
    )
    if activity_row is not None:
        out.actual_duration_seconds = _num(activity_row.get("duration_seconds"))
        out.actual_distance_meters = _num(activity_row.get("distance_meters"))
        out.actual_tss = _num(activity_row.get("training_stress_score"))
        out.actual_pace_sec_per_km = _pace_sec_per_km(
            out.actual_duration_seconds, out.actual_distance_meters
        )
    out.planned_duration_seconds = _num(planned_row.get("target_duration_seconds"))
    out.planned_distance_meters = _num(planned_row.get("target_distance_meters"))
    out.planned_tss = _num(planned_row.get("target_tss"))
    out.planned_pace_sec_per_km = _pace_sec_per_km(
        out.planned_duration_seconds, out.planned_distance_meters
    )
    out.duration_ratio = _ratio(
        out.actual_duration_seconds, out.planned_duration_seconds
    )
    out.distance_ratio = _ratio(out.actual_distance_meters, out.planned_distance_meters)
    return out


def week_adherence(
    sessions: list[SessionAdherence],
    *,
    week_number: Optional[int] = None,
    acwr_informational: Optional[dict] = None,
) -> WeekAdherence:
    """Aggregate per-session adherence into a week-level compliance report.

    Args:
        sessions: The week's per-session adherence rows.
        week_number: The plan week number, if scoped to one week.
        acwr_informational: Optional, clearly-labelled ACWR context. Never used
            to gate anything.

    Returns:
        A ``WeekAdherence`` with compliance % and planned/realized TSS.
    """
    planned_count = len(sessions)
    completed = [s for s in sessions if s.completed]
    completed_count = len(completed)
    compliance = (completed_count / planned_count * 100.0) if planned_count else 0.0
    planned_tss = sum(s.planned_tss or 0.0 for s in sessions)
    realized_tss = sum(s.actual_tss or 0.0 for s in completed)
    return WeekAdherence(
        week_number=week_number,
        planned_sessions=planned_count,
        completed_sessions=completed_count,
        compliance_pct=round(compliance, 1),
        planned_tss=round(planned_tss, 1),
        realized_tss=round(realized_tss, 1),
        sessions=sessions,
        acwr_informational=acwr_informational,
    )


def bucket_weekly_tss(
    activities: list[dict], window_end: date, *, weeks: int = 4
) -> list[float]:
    """Sum activity TSS into ``weeks`` trailing 7-day buckets ending at ``window_end``.

    Returns one TSS total per week, **oldest first** (so the last element is the
    most recent / acute week). Activities outside the trailing window are
    ignored.
    """
    buckets = [0.0] * weeks
    for act in activities:
        act_date = _as_date(act.get("start_timestamp"))
        if act_date is None:
            continue
        days_back = (window_end - act_date).days
        if days_back < 0 or days_back >= weeks * 7:
            continue
        week_idx = weeks - 1 - (days_back // 7)  # 0 = oldest, weeks-1 = current
        buckets[week_idx] += _num(act.get("training_stress_score")) or 0.0
    return [round(b, 1) for b in buckets]


def compute_acwr_informational(weekly_tss: list[float]) -> Optional[dict]:
    """Compute an ACWR-style ratio for context (never a decision rule).

    Acute = the most recent week's TSS; chronic = mean TSS over the available
    trailing weeks. Returns ``None`` when no load history is present.
    """
    series = [t for t in weekly_tss if t is not None]
    if not series:
        return None
    acute = series[-1]
    chronic = sum(series) / len(series)
    ratio = (acute / chronic) if chronic > 0 else None
    return {
        "value": round(ratio, 2) if ratio is not None else None,
        "acute_tss": round(acute, 1),
        "chronic_tss": round(chronic, 1),
        "weeks_used": len(series),
        "note": ACWR_CONTESTED_NOTE,
    }
