"""Unit tests for the adaptive coach Lot D4 (PROPOSE-ONLY weekly adjustment).

Covers the pure heuristics (maintain / insert-recovery / accelerate),
anti-thrashing (at most one structural change), pace-recompute gating, and two
mocked-pool orchestrator smokes: propose never mutates the plan, while the
explicit apply path does.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.training.adaptive.adherence import WeekAdherence
from src.training.adaptive.plan_adjuster import (
    AdjustmentAction,
    ProposedChange,
    _cap_structural_changes,
    maybe_recompute_paces,
    propose_weekly_adjustment,
    should_recompute_paces,
)
from src.training.adaptive.queries import apply_plan_adjustment, propose_plan_adjustment
from src.training.models import RaceObjective


def _week(*, planned=4, completed=4, planned_tss=300.0, realized_tss=300.0, num=3):
    return WeekAdherence(
        week_number=num,
        planned_sessions=planned,
        completed_sessions=completed,
        compliance_pct=round(completed / planned * 100.0, 1) if planned else 0.0,
        planned_tss=planned_tss,
        realized_tss=realized_tss,
    )


# ---------------------------------------------------------------------------
# propose_weekly_adjustment — heuristics
# ---------------------------------------------------------------------------


def test_on_track_holds_plan():
    wk = _week(planned=4, completed=4, planned_tss=300, realized_tss=295)
    p = propose_weekly_adjustment(wk, ["green"] * 7, from_week=3)
    assert p.target_week == 4
    assert p.auto_apply is False
    assert p.structural_change_count == 0
    assert p.changes[0].action == AdjustmentAction.MAINTAIN


def test_missed_sessions_do_not_pile_up():
    # 3/4 done, no fatigue -> keep next week stable, no structural change.
    wk = _week(planned=4, completed=3, planned_tss=300, realized_tss=220)
    p = propose_weekly_adjustment(wk, ["green", "green", "amber"], from_week=5)
    assert p.structural_change_count == 0
    assert p.changes[0].action == AdjustmentAction.MAINTAIN
    assert "do not pile" in p.changes[0].rationale.lower()


def test_sustained_fatigue_low_compliance_inserts_recovery():
    wk = _week(planned=4, completed=2, planned_tss=300, realized_tss=120)  # 50%
    verdicts = ["amber", "red", "amber", "red", "amber"]
    p = propose_weekly_adjustment(wk, verdicts, from_week=6)
    assert p.structural_change_count == 1
    change = p.changes[0]
    assert change.action == AdjustmentAction.INSERT_RECOVERY
    assert change.structural is True
    assert change.tss_factor == 0.6
    assert change.target_week == 7


def test_consistently_green_and_ahead_accelerates():
    wk = _week(planned=4, completed=4, planned_tss=300, realized_tss=320)
    p = propose_weekly_adjustment(wk, ["green"] * 8, from_week=2)
    assert p.structural_change_count == 1
    change = p.changes[0]
    assert change.action == AdjustmentAction.ACCELERATE
    assert change.tss_factor == 1.15
    assert "heuristic" in change.evidence_label


def test_ahead_but_fatigued_does_not_accelerate():
    # High compliance + ahead, but recent RED days -> no acceleration.
    wk = _week(planned=4, completed=4, planned_tss=300, realized_tss=320)
    p = propose_weekly_adjustment(wk, ["red", "red", "green"], from_week=2)
    assert all(c.action != AdjustmentAction.ACCELERATE for c in p.changes)


def test_anti_thrashing_caps_structural_changes():
    # Two structural changes collapse to one (non-structural preserved).
    changes = [
        ProposedChange(action=AdjustmentAction.INSERT_RECOVERY, structural=True),
        ProposedChange(action=AdjustmentAction.ACCELERATE, structural=True),
        ProposedChange(action=AdjustmentAction.MAINTAIN, structural=False),
    ]
    capped = _cap_structural_changes(changes)
    assert sum(1 for c in capped if c.structural) == 1
    assert any(not c.structural for c in capped)


# ---------------------------------------------------------------------------
# pace recompute gating
# ---------------------------------------------------------------------------


def test_should_recompute_paces_threshold():
    assert should_recompute_paces(14.5, 15.2) is True  # ~5% shift
    assert should_recompute_paces(14.5, 14.6) is False  # <1% shift
    assert should_recompute_paces(None, 15.0) is False
    assert should_recompute_paces(14.5, None) is False


def test_maybe_recompute_paces_returns_paceset_on_shift():
    paces = maybe_recompute_paces(
        14.5, 15.3, objective=RaceObjective.performance, target_time_seconds=12000
    )
    assert paces is not None
    assert paces.vma_kmh == 15.3
    assert "MPR" in paces.zones


def test_maybe_recompute_paces_none_on_small_shift():
    assert maybe_recompute_paces(14.5, 14.55) is None


# ---------------------------------------------------------------------------
# orchestrator smokes — mocked pool
# ---------------------------------------------------------------------------


def _plan_row():
    return {
        "id": 5,
        "user_id": 1,
        "start_date": date(2026, 6, 1),
        "end_date": date(2026, 8, 31),
        "total_weeks": 12,
    }


@pytest.mark.asyncio
async def test_propose_plan_adjustment_is_propose_only():
    """A proposal is persisted but NO plan rows are mutated (no execute)."""
    plan_row = _plan_row()
    planned = [
        {
            "id": 101,
            "planned_date": date(2026, 6, 2),
            "sport_type": "road_running",
            "session_type": "EF",
            "title": "EF",
            "target_duration_seconds": 3600,
            "target_distance_meters": 10000,
            "target_tss": 60,
        }
    ]
    window_acts = []  # missed -> compliance 0
    acwr_acts = []
    fitness_row = {
        "generation_params": '{"paces": {"vma_kmh": 14.5, "objective": "performance"}}',
        "manual_vma": 14.5,  # same VMA -> no pace recompute
    }
    proposal_row = {"id": 77, "status": "proposed"}

    pool = MagicMock()
    pool.fetchrow = AsyncMock(side_effect=[plan_row, fitness_row, proposal_row])
    pool.fetch = AsyncMock(
        side_effect=[planned, window_acts, acwr_acts, [{"verdict": "green"}]]
    )

    result = await propose_plan_adjustment(pool, 5, 1, week_number=1)

    assert result is not None
    assert result["proposal_id"] == 77
    assert result["auto_apply"] is False
    assert result["from_week"] == 1
    assert result["target_week"] == 2
    # Persisted a proposal, but never mutated a plan row.
    pool.execute.assert_not_called()


@pytest.mark.asyncio
async def test_propose_plan_adjustment_missing_plan_returns_none():
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value=None)
    pool.fetch = AsyncMock()
    assert await propose_plan_adjustment(pool, 999, 1, week_number=1) is None
    pool.execute.assert_not_called()


@pytest.mark.asyncio
async def test_apply_plan_adjustment_mutates_target_week():
    """The explicit apply path DOES write to the plan (the only one that may)."""
    stored = {
        "id": 77,
        "plan_id": 5,
        "user_id": 1,
        "status": "proposed",
        "proposal": (
            '{"changes": [{"action": "accelerate", "target_week": 4, '
            '"structural": true, "tss_factor": 1.15}]}'
        ),
    }
    week_row = {"id": 40, "target_tss": 300}
    applied_row = {"id": 77, "status": "applied", "applied": True}

    pool = MagicMock()
    pool.fetchrow = AsyncMock(side_effect=[stored, week_row, applied_row])
    pool.execute = AsyncMock()

    result = await apply_plan_adjustment(pool, 77, 1)

    assert result["status"] == "applied"
    pool.execute.assert_awaited_once()
    args = pool.execute.await_args.args
    assert args[1] == round(300 * 1.15)  # 345
    assert args[2] == 40


@pytest.mark.asyncio
async def test_apply_already_applied_is_noop():
    stored = {"id": 77, "plan_id": 5, "user_id": 1, "status": "applied", "proposal": "{}"}
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value=stored)
    pool.execute = AsyncMock()
    result = await apply_plan_adjustment(pool, 77, 1)
    assert result["status"] == "applied"
    pool.execute.assert_not_called()


@pytest.mark.asyncio
async def test_apply_missing_proposal_returns_none():
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value=None)
    pool.execute = AsyncMock()
    assert await apply_plan_adjustment(pool, 404, 1) is None
    pool.execute.assert_not_called()
