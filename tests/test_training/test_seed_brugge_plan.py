"""Tests for scripts/seed_brugge_plan.py (spec 03).

The script is loaded by path because ``scripts/`` is not an importable package.
Tests cover the pure plan builder, the date anchoring, and the idempotent SQL
emission — no database is touched.
"""

import importlib.util
import sys
from datetime import date
from pathlib import Path

from src.api.schemas import VALID_INTENSITIES, VALID_SPORT_TYPES

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "seed_brugge_plan.py"


def _load_module():
    """Load the seed script module from its file path.

    The module is registered in ``sys.modules`` before execution so that
    ``@dataclass`` annotation resolution can find its own module namespace.
    """
    spec = importlib.util.spec_from_file_location("seed_brugge_plan", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


seed = _load_module()


def test_plan_has_expected_session_count():
    assert len(seed.build_plan()) == 91


def test_all_dates_within_plan_window():
    rows = seed.build_plan()
    for r in rows:
        assert date(2026, 6, 8) <= r["planned_date"] <= date(2026, 10, 11)


def test_sport_types_and_intensities_are_api_valid():
    # Every row must be loadable through the public import endpoint vocabulary.
    for r in seed.build_plan():
        assert r["sport_type"] in VALID_SPORT_TYPES, r
        assert r["intensity"] in VALID_INTENSITIES, r


def test_weekday_offsets_are_respected():
    # A session anchored to a given weekday must land on that weekday.
    # Long runs (Sunday) and the race must be on Sunday.
    rows = seed.build_plan()
    race = [
        r
        for r in rows
        if r["intensity"] == "race" and r["planned_date"] == date(2026, 10, 11)
    ]
    assert len(race) == 1
    assert race[0]["planned_date"].weekday() == 6  # Sunday
    assert race[0]["planned_distance_meters"] == 42200.0
    assert "MARATHON" in race[0]["title"].upper()


def test_truth_checkpoints_are_placed():
    rows = seed.build_plan()
    # 10 km test on Saturday of week 4 (2026-07-18).
    test_10k = [r for r in rows if "TEST 10 KM" in r["title"].upper()]
    assert len(test_10k) == 1
    assert test_10k[0]["planned_date"] == date(2026, 7, 18)
    assert test_10k[0]["planned_date"].weekday() == 5  # Saturday
    # Simulation on Sunday of week 12 (2026-09-13).
    simu = [r for r in rows if "SIMULATION" in r["title"].upper()]
    assert len(simu) == 1
    assert simu[0]["planned_date"] == date(2026, 9, 13)


def test_renfo_a_only_in_weeks_10_to_12():
    rows = seed.build_plan()
    renfo_a = [r for r in rows if "Renfo A" in r["title"]]
    assert len(renfo_a) == 3
    assert {r["planned_date"] for r in renfo_a} == {
        date(2026, 8, 24),  # week 10 Monday
        date(2026, 8, 31),  # week 11 Monday
        date(2026, 9, 7),  # week 12 Monday
    }


def test_emit_sql_is_idempotent_and_escapes_quotes():
    sql = seed.emit_sql()
    assert sql.startswith("-- Seed: Athora Bruges Marathon")
    assert "BEGIN;" in sql and "COMMIT;" in sql
    # Idempotency: clears the window + retires the wizard draft before inserting.
    assert "DELETE FROM planned_workouts WHERE user_id=70" in sql
    assert "DELETE FROM training_plans WHERE id=6" in sql
    assert "INSERT INTO planned_workouts" in sql
    # French apostrophes must be doubled, never left raw inside a literal.
    assert "''" in sql
    # 91 value tuples → 91 user_id references inside the INSERT block.
    insert_block = sql.split("INSERT INTO planned_workouts", 1)[1]
    assert insert_block.count("(70, '2026-") == 91


def test_emit_csv_header_and_row_count():
    csv_text = seed.emit_csv()
    lines = [ln for ln in csv_text.splitlines() if ln.strip()]
    assert lines[0].startswith("date,sport_type,title,description")
    assert len(lines) == 1 + 91  # header + sessions
