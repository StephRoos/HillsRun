"""Smoke tests for scripts/seed_marathon_plan.py (Lot 7).

The script is loaded by path because ``scripts/`` is not an importable package.
Tests cover the pure markdown renderer and an end-to-end smoke of
``seed_and_generate`` against a mocked pool with ``generate_plan`` patched, so
no real database is required.
"""

import importlib.util
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.training.pace_calculator import compute_paces
from src.training.models import RaceObjective

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "seed_marathon_plan.py"
)


def _load_module():
    """Load the seed script module from its file path."""
    spec = importlib.util.spec_from_file_location("seed_marathon_plan", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seed = _load_module()


def _sample_paces():
    return compute_paces(
        14.5,
        objective=RaceObjective.performance,
        target_time_seconds=12600,
    )


def test_render_plan_markdown_structure():
    """The renderer emits overview, pace table and per-week sections."""
    paces = _sample_paces()
    plan = {
        "name": "Marathon de Brugge — Plan route",
        "total_weeks": 2,
        "start_date": "2026-06-01",
        "end_date": "2026-10-12",
        "status": "draft",
    }
    race = {
        "race_name": "Marathon de Brugge",
        "race_date": date(2026, 10, 12),
        "distance_km": 42.195,
        "objective": "performance",
        "target_time_seconds": 12600,
    }
    weeks = [
        {
            "id": 10,
            "week_number": 1,
            "phase": "development",
            "is_recovery_week": False,
            "target_volume_km": 50,
            "target_tss": 320.0,
            "target_sessions": 5,
            "notes": "",
        },
        {
            "id": 11,
            "week_number": 2,
            "phase": "specific",
            "is_recovery_week": False,
            "target_volume_km": 60,
            "target_tss": 360.0,
            "target_sessions": 5,
            "notes": "",
        },
    ]
    sessions_by_week = {
        10: [
            {
                "day_of_week": 4,
                "session_type": "MPR",
                "title": "Allure marathon",
                "target_duration_seconds": 3600,
                "target_distance_meters": None,
                "target_tss": 62.0,
                "hr_zone_primary": 3,
            }
        ],
        11: [
            {
                "day_of_week": 7,
                "session_type": "SL",
                "title": "Sortie longue",
                "target_duration_seconds": 9000,
                "target_distance_meters": 29500,
                "target_tss": 120.0,
                "hr_zone_primary": 2,
            }
        ],
    }

    md = seed.render_plan_markdown(plan, race, paces, weeks, sessions_by_week)

    assert "# Marathon de Brugge — Plan route" in md
    assert "## Allures" in md
    assert "Semaine 1" in md and "Semaine 2" in md
    assert "MPR" in md and "SL" in md
    # MPR pace label (4:59 /km) should appear in the MPR row.
    assert paces.pace_for("MPR").label in md
    # Long run distance rendered in km.
    assert "29.5 km" in md
    # Target time rendered as 3h30.
    assert "3h30" in md


def test_session_pace_label_unmapped_returns_dash():
    """Strength/rest sessions have no pace and render as a dash."""
    paces = _sample_paces()
    assert seed._session_pace_label("RMU", paces) == "—"
    assert seed._session_pace_label("EF", None) == "—"
    assert seed._session_pace_label("MPR", paces) == paces.pace_for("MPR").label


def test_fmt_helpers():
    """Duration and distance formatters handle missing values."""
    assert seed._fmt_duration(None) == "—"
    assert seed._fmt_duration(3600) == "1h00"
    assert seed._fmt_duration(1800) == "30min"
    assert seed._fmt_distance(None) == "—"
    assert seed._fmt_distance(29500) == "29.5 km"


@pytest.mark.asyncio
async def test_seed_and_generate_writes_markdown(tmp_path):
    """End-to-end smoke: seed + generate (mocked) produces a markdown file."""
    pool = AsyncMock()
    # set_manual_vma UPDATE ... RETURNING
    pool.fetchrow = AsyncMock(return_value={"user_id": 1})

    out_path = tmp_path / "mon-plan-marathon.md"

    race_row = {
        "id": 7,
        "race_name": "Marathon de Brugge",
        "race_date": date(2026, 10, 12),
        "distance_km": 42.195,
        "objective": "performance",
        "target_time_seconds": 12600,
        "discipline": "road",
    }
    paces = _sample_paces()
    plan_row = {
        "id": 99,
        "name": "Marathon de Brugge — Plan route",
        "total_weeks": 1,
        "start_date": "2026-06-01",
        "end_date": "2026-10-12",
        "status": "draft",
        "generation_params": {"paces": paces.model_dump(mode="json")},
    }
    week_rows = [
        {
            "id": 1,
            "week_number": 1,
            "phase": "development",
            "is_recovery_week": False,
            "target_volume_km": 50,
            "target_tss": 320.0,
            "target_sessions": 4,
            "notes": "",
        }
    ]
    session_rows = [
        {
            "day_of_week": 4,
            "session_type": "MPR",
            "title": "Allure marathon",
            "target_duration_seconds": 3600,
            "target_distance_meters": None,
            "target_tss": 62.0,
            "hr_zone_primary": 3,
        }
    ]

    with patch.object(seed.db_ops, "upsert_athlete_profile", AsyncMock()), \
         patch.object(seed.db_ops, "list_race_targets", AsyncMock(return_value=[])), \
         patch.object(seed.db_ops, "create_race_target", AsyncMock(return_value=race_row)), \
         patch.object(seed.db_ops, "list_training_plans", AsyncMock(return_value=([], 0))), \
         patch.object(seed.db_ops, "get_training_plan", AsyncMock(return_value=plan_row)), \
         patch.object(seed.db_ops, "get_plan_weeks", AsyncMock(return_value=week_rows)), \
         patch.object(seed.db_ops, "get_plan_sessions_for_week", AsyncMock(return_value=session_rows)), \
         patch.object(seed, "generate_plan", AsyncMock(return_value={
             "plan_id": 99,
             "name": "Marathon de Brugge — Plan route",
             "total_weeks": 1,
             "start_date": "2026-06-01",
             "end_date": "2026-10-12",
             "status": "draft",
         })):
        result = await seed.seed_and_generate(pool, user_id=1, out_path=out_path)

    assert result == out_path
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert "Marathon de Brugge" in content
    assert "Semaine 1" in content
    assert "MPR" in content
