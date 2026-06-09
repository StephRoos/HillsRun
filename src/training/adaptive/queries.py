"""Async DB helpers for the adaptive coach (Lot D1).

Read-only signal fetchers plus a single upsert into ``daily_recommendations``.
Kept separate from ``readiness`` so the verdict logic stays pure and testable.
All HRV values use ``hrv_data.last_night_avg`` (the overnight rMSSD average).
"""

import asyncio
import json
import math
from datetime import date, timedelta
from typing import Any, Optional

from .readiness import (
    DailyVerdict,
    SecondaryModifiers,
    build_hrv_baseline,
    daily_verdict,
)
from .readiness_agent import AgentRecommendation, build_agent_recommendation

# Trailing window (days) used to build both the HRV and resting-HR baselines.
_BASELINE_WINDOW_DAYS = 60


async def fetch_hrv_series(
    pool, user_id: int, end: date, *, window_days: int = _BASELINE_WINDOW_DAYS
) -> list[float]:
    """Fetch overnight HRV values over the trailing window ending at ``end``.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.
        end: Last calendar date included (inclusive).
        window_days: Size of the trailing window in days.

    Returns:
        List of ``last_night_avg`` values (ms), oldest first, nulls excluded.
    """
    start = end - timedelta(days=window_days)
    rows = await pool.fetch(
        """
        SELECT last_night_avg
        FROM hrv_data
        WHERE user_id = $1
          AND calendar_date > $2
          AND calendar_date <= $3
          AND last_night_avg IS NOT NULL
        ORDER BY calendar_date ASC
        """,
        user_id,
        start,
        end,
    )
    return [float(r["last_night_avg"]) for r in rows]


async def fetch_hrv_value(pool, user_id: int, day: date) -> Optional[float]:
    """Fetch a single day's overnight HRV value, or ``None`` if absent."""
    value = await pool.fetchval(
        """
        SELECT last_night_avg
        FROM hrv_data
        WHERE user_id = $1 AND calendar_date = $2
        """,
        user_id,
        day,
    )
    return float(value) if value is not None else None


async def fetch_secondary_modifiers(
    pool, user_id: int, day: date
) -> SecondaryModifiers:
    """Fetch the non-validated secondary signals for ``day``.

    Resting-HR baseline is the trailing-60-day average resting heart rate.
    """
    sleep_score = await pool.fetchval(
        "SELECT sleep_score FROM sleep_data WHERE user_id = $1 AND calendar_date = $2",
        user_id,
        day,
    )
    resting_hr = await pool.fetchval(
        """
        SELECT resting_heart_rate FROM daily_summary
        WHERE user_id = $1 AND calendar_date = $2
        """,
        user_id,
        day,
    )
    resting_hr_baseline = await pool.fetchval(
        """
        SELECT AVG(resting_heart_rate) FROM daily_summary
        WHERE user_id = $1
          AND calendar_date > $2
          AND calendar_date <= $3
          AND resting_heart_rate IS NOT NULL
        """,
        user_id,
        day - timedelta(days=_BASELINE_WINDOW_DAYS),
        day,
    )
    training_readiness = await pool.fetchval(
        "SELECT score FROM training_readiness WHERE user_id = $1 AND calendar_date = $2",
        user_id,
        day,
    )
    return SecondaryModifiers(
        sleep_score=float(sleep_score) if sleep_score is not None else None,
        resting_hr=float(resting_hr) if resting_hr is not None else None,
        resting_hr_baseline=(
            float(resting_hr_baseline) if resting_hr_baseline is not None else None
        ),
        training_readiness=(
            float(training_readiness) if training_readiness is not None else None
        ),
    )


async def evaluate_daily_readiness(
    pool, user_id: int, day: date, *, persist: bool = True
) -> DailyVerdict:
    """Compute today's readiness verdict from stored Garmin signals.

    Builds the trailing baseline, reads today's HRV plus secondary signals,
    resolves the two-day RED hysteresis from yesterday's value, then runs the
    pure ``daily_verdict`` rule. Optionally persists the result. This never
    mutates the training plan.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.
        day: Day to evaluate (typically today).
        persist: When True, upsert the result into ``daily_recommendations``.

    Returns:
        The computed ``DailyVerdict``.
    """
    series = await fetch_hrv_series(pool, user_id, day)
    baseline = build_hrv_baseline(series)
    today_hrv = await fetch_hrv_value(pool, user_id, day)
    secondary = await fetch_secondary_modifiers(pool, user_id, day)

    prev_day_below_red = False
    if baseline is not None:
        yesterday_hrv = await fetch_hrv_value(pool, user_id, day - timedelta(days=1))
        if yesterday_hrv is not None and yesterday_hrv > 0:
            prev_day_below_red = math.log(yesterday_hrv) < baseline.red_threshold_ln

    result = daily_verdict(
        today_hrv,
        baseline,
        secondary=secondary,
        prev_day_below_red=prev_day_below_red,
    )

    if persist:
        await upsert_daily_recommendation(pool, user_id, day, result)
    return result


async def upsert_daily_recommendation(
    pool, user_id: int, day: date, result: DailyVerdict
) -> dict[str, Any]:
    """Persist (or refresh) the day's recommendation. Never mutates the plan.

    Returns:
        The stored row as a dict.
    """
    row = await pool.fetchrow(
        """
        INSERT INTO daily_recommendations
            (user_id, date, verdict, reason, suggested_modification,
             hrv_value, baseline_low, baseline_high)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (user_id, date) DO UPDATE SET
            verdict = EXCLUDED.verdict,
            reason = EXCLUDED.reason,
            suggested_modification = EXCLUDED.suggested_modification,
            hrv_value = EXCLUDED.hrv_value,
            baseline_low = EXCLUDED.baseline_low,
            baseline_high = EXCLUDED.baseline_high
        RETURNING *
        """,
        user_id,
        day,
        result.verdict.value,
        result.reason,
        json.dumps(result.suggested_modification),
        result.hrv_value,
        result.baseline_low,
        result.baseline_high,
    )
    return dict(row)


# ---------------------------------------------------------------------------
# Lot D2 — AI reasoning layer (non-destructive). Reads context, runs the agent
# off the event loop, and persists the rationale next to the D1 verdict.
# ---------------------------------------------------------------------------


async def fetch_planned_session(pool, user_id: int, day: date) -> Optional[dict]:
    """Fetch the planned workout for ``day`` (first match), or ``None``."""
    row = await pool.fetchrow(
        """
        SELECT title, sport_type, description, planned_duration_seconds,
               planned_distance_meters, intensity
        FROM planned_workouts
        WHERE user_id = $1 AND planned_date = $2
        ORDER BY id ASC
        LIMIT 1
        """,
        user_id,
        day,
    )
    return dict(row) if row is not None else None


async def fetch_recent_context(
    pool, user_id: int, day: date, *, days: int = 3
) -> list[dict]:
    """Fetch the prior ``days`` daily recommendations (oldest first).

    Used to give the agent short-term context without re-running the rule.
    """
    rows = await pool.fetch(
        """
        SELECT date, verdict, hrv_value
        FROM daily_recommendations
        WHERE user_id = $1 AND date < $2
        ORDER BY date DESC
        LIMIT $3
        """,
        user_id,
        day,
        days,
    )
    return [
        {
            "date": r["date"].isoformat(),
            "verdict": r["verdict"],
            "hrv_value": float(r["hrv_value"]) if r["hrv_value"] is not None else None,
        }
        for r in reversed(rows)
    ]


async def persist_agent_recommendation(
    pool, user_id: int, day: date, rec: AgentRecommendation
) -> Optional[dict]:
    """Store the agent's rationale on the existing D1 row. Never mutates a plan.

    Updates only the AI columns; the authoritative ``verdict`` column written by
    D1 is left untouched. Returns the updated row, or ``None`` if no D1 row
    exists yet for ``(user_id, day)``.
    """
    row = await pool.fetchrow(
        """
        UPDATE daily_recommendations
        SET ai_rationale = $3,
            ai_recommendation = $4,
            ai_model = $5,
            ai_generated_at = CURRENT_TIMESTAMP
        WHERE user_id = $1 AND date = $2
        RETURNING *
        """,
        user_id,
        day,
        rec.rationale,
        json.dumps(rec.model_dump(mode="json")),
        rec.model,
    )
    return dict(row) if row is not None else None


async def explain_daily_readiness(
    pool,
    user_id: int,
    day: date,
    base_result: DailyVerdict,
    *,
    persist: bool = True,
    client: Any = None,
    model: Optional[str] = None,
) -> AgentRecommendation:
    """Run the AI reasoning layer for an already-computed D1 verdict.

    Fetches the planned session and 3-day context, runs the (blocking) Claude
    call off the event loop, optionally persists the rationale, and returns the
    structured recommendation. The agent never relaxes ``base_result``.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.
        day: Day being explained.
        base_result: The authoritative D1 verdict (anchor).
        persist: When True, store the rationale on the D1 row.
        client: Optional Anthropic client (injected in tests).
        model: Optional model override (defaults to Haiku 4.5).

    Returns:
        The ``AgentRecommendation``.
    """
    planned_session = await fetch_planned_session(pool, user_id, day)
    recent_context = await fetch_recent_context(pool, user_id, day)

    kwargs: dict[str, Any] = {
        "planned_session": planned_session,
        "recent_context": recent_context,
        "client": client,
    }
    if model is not None:
        kwargs["model"] = model

    # The Anthropic SDK call is synchronous — run it in a worker thread so the
    # FastAPI event loop is never blocked (ADR-007 spirit).
    rec = await asyncio.to_thread(build_agent_recommendation, base_result, **kwargs)

    if persist:
        await persist_agent_recommendation(pool, user_id, day, rec)
    return rec


# ---------------------------------------------------------------------------
# Lot D3 — planned vs actual reconciliation (READ-ONLY). Nothing here writes.
# ---------------------------------------------------------------------------


async def fetch_planned_for_plan(
    pool, plan_id: int, start: date, end: date
) -> list[dict]:
    """Fetch a plan's planned workouts within ``[start, end]`` (inclusive).

    ``target_tss`` lives on ``training_plan_sessions`` (planned_workouts has no
    such column), so it is joined in via the dual-write link
    ``training_plan_sessions.planned_workout_id``.
    """
    rows = await pool.fetch(
        """
        SELECT pw.id, pw.planned_date, pw.sport_type, pw.session_type, pw.title,
               pw.planned_duration_seconds AS target_duration_seconds,
               pw.planned_distance_meters AS target_distance_meters,
               s.target_tss AS target_tss
        FROM planned_workouts pw
        LEFT JOIN training_plan_sessions s ON s.planned_workout_id = pw.id
        WHERE pw.plan_id = $1
          AND pw.planned_date >= $2
          AND pw.planned_date <= $3
        ORDER BY pw.planned_date ASC, pw.id ASC
        """,
        plan_id,
        start,
        end,
    )
    return [dict(r) for r in rows]


async def fetch_activities_in_range(
    pool, user_id: int, start: date, end: date
) -> list[dict]:
    """Fetch a user's running-relevant activities whose start date is in range.

    Range is inclusive; ``end`` is bumped by a day in the query so the whole of
    the last calendar day is covered regardless of start time.
    """
    rows = await pool.fetch(
        """
        SELECT activity_id, activity_name, activity_type, sport_type,
               start_timestamp, duration_seconds, distance_meters,
               average_pace, training_stress_score
        FROM activities
        WHERE user_id = $1
          AND start_timestamp >= $2
          AND start_timestamp < $3
        ORDER BY start_timestamp ASC
        """,
        user_id,
        start,
        end + timedelta(days=1),
    )
    return [dict(r) for r in rows]


async def reconcile_plan(
    pool, plan_id: int, user_id: int, *, week_number: Optional[int] = None
) -> Optional[dict]:
    """Build a read-only planned-vs-actual report for a plan (or one week).

    Matches planned workouts to completed activities (+/-1 day tolerance),
    computes per-session and weekly compliance, realized TSS, and an
    informational-only ACWR. Never mutates the plan or the activities.

    Args:
        pool: asyncpg connection pool.
        plan_id: Training plan ID.
        user_id: Garmin user ID (ownership check).
        week_number: When given, scope to that 1-based plan week; else the
            whole plan window.

    Returns:
        A JSON-serialisable report dict, or ``None`` if the plan is not found.
    """
    # Imported here to keep the pure adherence/matcher modules import-light and
    # avoid any chance of a circular import at package load time.
    from .adherence import (
        bucket_weekly_tss,
        build_session_adherence,
        compute_acwr_informational,
        week_adherence,
    )
    from .workout_matcher import match_workouts
    from ..db_operations import get_training_plan

    plan = await get_training_plan(pool, plan_id, user_id)
    if plan is None:
        return None

    start_date: date = plan["start_date"]
    if week_number is not None:
        window_start = start_date + timedelta(days=(week_number - 1) * 7)
        window_end = window_start + timedelta(days=6)
    else:
        window_start = start_date
        window_end = plan["end_date"]

    planned = await fetch_planned_for_plan(pool, plan_id, window_start, window_end)
    # Widen the activity fetch by the day tolerance on each side.
    activities = await fetch_activities_in_range(
        pool,
        user_id,
        window_start - timedelta(days=1),
        window_end + timedelta(days=1),
    )

    matches = match_workouts(planned, activities)
    planned_by_id = {p.get("id"): p for p in planned}
    activity_by_id = {a.get("activity_id"): a for a in activities}

    sessions = [
        build_session_adherence(
            m,
            planned_by_id.get(m.planned_id, {}),
            activity_by_id.get(m.activity_id) if m.matched else None,
        )
        for m in matches
    ]

    # ACWR (informational only): trailing 4 weeks of activity TSS ending at the
    # window end. Never feeds a decision — exposed with a contested note.
    acwr_activities = await fetch_activities_in_range(
        pool, user_id, window_end - timedelta(days=27), window_end
    )
    acwr = compute_acwr_informational(bucket_weekly_tss(acwr_activities, window_end))

    week_report = week_adherence(
        sessions, week_number=week_number, acwr_informational=acwr
    )

    return {
        "plan_id": plan_id,
        "week_number": week_number,
        "window": {
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
        },
        "adherence": week_report.model_dump(mode="json"),
        "matches": [m.model_dump(mode="json") for m in matches],
    }


# ---------------------------------------------------------------------------
# Lot D4 — weekly adjustment (PROPOSE-ONLY). Persisting a *proposal* never
# mutates the plan; only apply_plan_adjustment (explicit user action) writes to
# training_plan_weeks / training_plan_sessions.
# ---------------------------------------------------------------------------


async def fetch_recent_verdicts(
    pool, user_id: int, end_iso: str, *, days: int = 10
) -> list[str]:
    """Fetch the trailing daily readiness verdicts ending at ``end_iso``.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.
        end_iso: Window end as an ISO date string (inclusive).
        days: Size of the trailing window.

    Returns:
        Verdict strings (oldest first), e.g. ``["green", "amber", ...]``.
    """
    end = date.fromisoformat(end_iso)
    rows = await pool.fetch(
        """
        SELECT verdict
        FROM daily_recommendations
        WHERE user_id = $1 AND date > $2 AND date <= $3
        ORDER BY date ASC
        """,
        user_id,
        end - timedelta(days=days),
        end,
    )
    return [r["verdict"] for r in rows]


def _parse_generation_params(raw: Any) -> dict:
    """Coerce a possibly JSON-encoded generation_params value to a dict."""
    if raw is None:
        return {}
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return {}
    if isinstance(raw, dict):
        return raw
    return {}


async def fetch_plan_fitness_context(
    pool, plan_id: int, user_id: int
) -> Optional[dict]:
    """Fetch the data needed to decide whether to recompute paces.

    Pulls the plan's stored paces (from ``generation_params``) and the athlete's
    latest manual VMA, so the caller can compare the two. Read-only.

    Returns:
        ``{"current_vma_kmh", "new_vma_kmh", "objective", "target_time_seconds",
        "generation_params"}`` or ``None`` if the plan is absent.
    """
    row = await pool.fetchrow(
        """
        SELECT p.generation_params, gu.manual_vma
        FROM training_plans p
        JOIN garmin_user gu ON gu.user_id = p.user_id
        WHERE p.id = $1 AND p.user_id = $2
        """,
        plan_id,
        user_id,
    )
    if row is None:
        return None
    gp = _parse_generation_params(row["generation_params"])
    paces = gp.get("paces") or {}
    new_vma = row["manual_vma"]
    return {
        "current_vma_kmh": paces.get("vma_kmh"),
        "new_vma_kmh": float(new_vma) if new_vma is not None else None,
        "objective": paces.get("objective"),
        "target_time_seconds": paces.get("target_time_seconds"),
        "generation_params": gp,
    }


async def insert_weekly_reconciliation(
    pool, plan_id: int, user_id: int, proposal: Any
) -> dict:
    """Persist a propose-only adjustment. Does NOT mutate the plan.

    One live proposal per evaluated week (``UNIQUE(plan_id, from_week)``); a
    re-run refreshes it and resets it to ``proposed``.

    Returns:
        The stored ``weekly_reconciliations`` row as a dict.
    """
    row = await pool.fetchrow(
        """
        INSERT INTO weekly_reconciliations
            (plan_id, user_id, from_week, target_week, compliance_pct, proposal,
             status, applied)
        VALUES ($1, $2, $3, $4, $5, $6, 'proposed', FALSE)
        ON CONFLICT (plan_id, from_week) DO UPDATE SET
            target_week = EXCLUDED.target_week,
            compliance_pct = EXCLUDED.compliance_pct,
            proposal = EXCLUDED.proposal,
            status = 'proposed',
            applied = FALSE,
            applied_at = NULL,
            created_at = CURRENT_TIMESTAMP
        RETURNING *
        """,
        plan_id,
        user_id,
        proposal.from_week,
        proposal.target_week,
        proposal.compliance_pct,
        json.dumps(proposal.model_dump(mode="json")),
    )
    return dict(row)


async def propose_plan_adjustment(
    pool, plan_id: int, user_id: int, *, week_number: int, persist: bool = True
) -> Optional[dict]:
    """Generate (and optionally persist) a propose-only weekly adjustment.

    Builds the read-only adherence report for ``week_number``, reads the recent
    daily verdicts, runs the pure heuristics, and — when VMA has shifted
    meaningfully — attaches a pace recompute. Persisting the proposal writes only
    to ``weekly_reconciliations``; the plan rows are never touched here.

    Args:
        pool: asyncpg connection pool.
        plan_id: Training plan ID.
        user_id: Garmin user ID (ownership check).
        week_number: The evaluated (just-completed) 1-based plan week.
        persist: When True, store the proposal in ``weekly_reconciliations``.

    Returns:
        A JSON-serialisable proposal dict, or ``None`` if the plan is absent.
    """
    # Imported lazily to keep the pure adjuster import-light and dodge cycles.
    from .plan_adjuster import (
        AdjustmentAction,
        ProposedChange,
        maybe_recompute_paces,
        propose_weekly_adjustment,
    )
    from .adherence import WeekAdherence
    from ..models import RaceObjective

    report = await reconcile_plan(pool, plan_id, user_id, week_number=week_number)
    if report is None:
        return None

    week_report = WeekAdherence(**report["adherence"])
    recent_verdicts = await fetch_recent_verdicts(
        pool, user_id, report["window"]["end"]
    )

    proposal = propose_weekly_adjustment(
        week_report, recent_verdicts, from_week=week_number
    )

    # Pace recompute (non-structural): only when the latest VMA has shifted past
    # the threshold versus the VMA the plan's paces were built from.
    context = await fetch_plan_fitness_context(pool, plan_id, user_id)
    if context is not None:
        objective = RaceObjective.finish
        if context.get("objective"):
            try:
                objective = RaceObjective(context["objective"])
            except ValueError:
                objective = RaceObjective.finish
        new_paces = maybe_recompute_paces(
            context.get("current_vma_kmh"),
            context.get("new_vma_kmh"),
            objective=objective,
            target_time_seconds=context.get("target_time_seconds"),
        )
        if new_paces is not None:
            proposal.recomputed_paces = new_paces.model_dump(mode="json")
            proposal.changes.append(
                ProposedChange(
                    action=AdjustmentAction.RECOMPUTE_PACES,
                    target_week=proposal.target_week,
                    structural=False,
                    rationale=(
                        f"VMA shifted from {context['current_vma_kmh']:.1f} to "
                        f"{context['new_vma_kmh']:.1f} km/h — refresh target paces."
                    ),
                )
            )

    stored: dict = {}
    if persist:
        stored = await insert_weekly_reconciliation(pool, plan_id, user_id, proposal)

    return {
        "proposal_id": stored.get("id"),
        "plan_id": plan_id,
        "from_week": proposal.from_week,
        "target_week": proposal.target_week,
        "status": stored.get("status", "proposed"),
        "auto_apply": False,
        "proposal": proposal.model_dump(mode="json"),
    }


async def apply_plan_adjustment(pool, proposal_id: int, user_id: int) -> Optional[dict]:
    """Apply a stored proposal to the plan — the ONLY plan-mutating path (D4).

    Requires an explicit call (no auto-apply). Idempotent: a proposal already
    ``applied`` is returned unchanged. Structural changes adjust the target
    week's ``target_tss`` (and recovery flag); a pace recompute refreshes the
    plan's ``generation_params``.

    Args:
        pool: asyncpg connection pool.
        proposal_id: ``weekly_reconciliations`` row ID.
        user_id: Garmin user ID (ownership check).

    Returns:
        The updated proposal row as a dict, or ``None`` if not found/owned.
    """
    row = await pool.fetchrow(
        "SELECT * FROM weekly_reconciliations WHERE id = $1 AND user_id = $2",
        proposal_id,
        user_id,
    )
    if row is None:
        return None
    if row["status"] == "applied":
        return dict(row)

    plan_id = row["plan_id"]
    proposal = _parse_generation_params(row["proposal"])  # same JSON coercion
    changes = proposal.get("changes", [])

    for change in changes:
        action = change.get("action")
        target_week = change.get("target_week")
        factor = change.get("tss_factor")

        if action in ("accelerate", "insert_recovery") and target_week and factor:
            week_row = await pool.fetchrow(
                """
                SELECT id, target_tss FROM training_plan_weeks
                WHERE plan_id = $1 AND week_number = $2
                """,
                plan_id,
                target_week,
            )
            if week_row is None:
                continue
            current_tss = week_row["target_tss"] or 0
            new_tss = round(float(current_tss) * factor)
            if action == "insert_recovery":
                await pool.execute(
                    """
                    UPDATE training_plan_weeks
                    SET target_tss = $1, is_recovery_week = TRUE
                    WHERE id = $2
                    """,
                    new_tss,
                    week_row["id"],
                )
            else:  # accelerate
                await pool.execute(
                    "UPDATE training_plan_weeks SET target_tss = $1 WHERE id = $2",
                    new_tss,
                    week_row["id"],
                )

        elif action == "recompute_paces" and proposal.get("recomputed_paces"):
            gp_raw = await pool.fetchval(
                "SELECT generation_params FROM training_plans WHERE id = $1",
                plan_id,
            )
            gp = _parse_generation_params(gp_raw)
            gp["paces"] = proposal["recomputed_paces"]
            await pool.execute(
                "UPDATE training_plans SET generation_params = $1 WHERE id = $2",
                json.dumps(gp),
                plan_id,
            )

    updated = await pool.fetchrow(
        """
        UPDATE weekly_reconciliations
        SET status = 'applied', applied = TRUE, applied_at = CURRENT_TIMESTAMP
        WHERE id = $1
        RETURNING *
        """,
        proposal_id,
    )
    return dict(updated)
