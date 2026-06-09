"""Unit tests for the adaptive coach Lot D1 (HRV-baseline daily readiness)."""

import math

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.training.adaptive.readiness import (
    SecondaryModifiers,
    Verdict,
    build_hrv_baseline,
    daily_verdict,
)
from src.training.adaptive.queries import evaluate_daily_readiness


# A varied 30-day series (50-54 ms) gives a real baseline with sd > 0.
_SERIES = [50 + (i % 5) for i in range(30)]


@pytest.fixture
def baseline():
    return build_hrv_baseline(_SERIES)


# --------------------------------------------------------------------------
# build_hrv_baseline
# --------------------------------------------------------------------------


def test_build_baseline_insufficient_points():
    """Fewer than 28 valid points -> no baseline (caller falls back)."""
    assert build_hrv_baseline([50.0] * 27) is None


def test_build_baseline_ignores_null_and_nonpositive():
    """None and non-positive HRV values are dropped before the count check."""
    values = [None, 0, -3] + [50.0] * 27  # only 27 valid -> still insufficient
    assert build_hrv_baseline(values) is None


def test_build_baseline_ok(baseline):
    """28+ points -> baseline with positive sd and band ordering."""
    assert baseline is not None
    assert baseline.n_points == 30
    assert baseline.sd_ln > 0
    assert baseline.low < baseline.high
    assert baseline.red_threshold_ln < baseline.lower_ln


# --------------------------------------------------------------------------
# daily_verdict — band logic
# --------------------------------------------------------------------------


def test_green_within_band(baseline):
    """A value at the mean is GREEN and proposes proceeding unchanged."""
    today = math.exp(baseline.mean_ln)
    result = daily_verdict(today, baseline)
    assert result.verdict is Verdict.GREEN
    assert result.suggested_modification["action"] == "proceed"


def test_amber_below_lower_bound(baseline):
    """Just below the lower band bound -> AMBER (ease the session)."""
    today = baseline.low * 0.99
    result = daily_verdict(today, baseline)
    assert result.verdict is Verdict.AMBER
    assert result.suggested_modification["downgrade_quality_to_easy"] is True
    assert result.suggested_modification["duration_pct"] == 75


def test_red_two_consecutive_deep_days(baseline):
    """Deep suppression for a second day -> RED (rest / active recovery)."""
    today = math.exp(baseline.red_threshold_ln) * 0.98
    result = daily_verdict(today, baseline, prev_day_below_red=True)
    assert result.verdict is Verdict.RED
    assert result.suggested_modification["action"] == "rest"


def test_red_requires_two_days_not_one(baseline):
    """A single deep dip (no prior deep day) is AMBER, not RED (hysteresis)."""
    today = math.exp(baseline.red_threshold_ln) * 0.98
    result = daily_verdict(today, baseline, prev_day_below_red=False)
    assert result.verdict is Verdict.AMBER


def test_hysteresis_single_dip_inside_band_stays_green(baseline):
    """A dip below the mean but still inside the band stays GREEN."""
    # Halfway between lower bound and mean -> inside band, below mean.
    today_ln = (baseline.lower_ln + baseline.mean_ln) / 2
    result = daily_verdict(math.exp(today_ln), baseline)
    assert result.verdict is Verdict.GREEN


# --------------------------------------------------------------------------
# daily_verdict — fallback & secondary modifiers
# --------------------------------------------------------------------------


def test_insufficient_baseline_fallback():
    """No baseline -> insufficient_baseline verdict, planned session kept."""
    result = daily_verdict(48.0, None)
    assert result.verdict is Verdict.INSUFFICIENT_BASELINE
    assert result.suggested_modification["action"] == "proceed"


def test_missing_today_value_falls_back(baseline):
    """A missing morning value also falls back to insufficient_baseline."""
    result = daily_verdict(None, baseline)
    assert result.verdict is Verdict.INSUFFICIENT_BASELINE


def test_secondary_nudges_borderline_green_to_amber(baseline):
    """Borderline GREEN (lower half of band) + bad sleep -> AMBER."""
    today_ln = (baseline.lower_ln + baseline.mean_ln) / 2  # below mean, in band
    secondary = SecondaryModifiers(sleep_score=40)
    result = daily_verdict(math.exp(today_ln), baseline, secondary=secondary)
    assert result.verdict is Verdict.AMBER


def test_secondary_alone_cannot_downgrade_comfortable_green(baseline):
    """A comfortable GREEN (above the mean) is not downgraded by secondaries."""
    today = math.exp(baseline.upper_ln)  # above the mean
    secondary = SecondaryModifiers(
        sleep_score=10, resting_hr=70, resting_hr_baseline=50, training_readiness=5
    )
    result = daily_verdict(today, baseline, secondary=secondary)
    assert result.verdict is Verdict.GREEN


def test_secondary_never_overrides_red(baseline):
    """Good secondary signals never lift a RED verdict."""
    today = math.exp(baseline.red_threshold_ln) * 0.98
    secondary = SecondaryModifiers(
        sleep_score=99, resting_hr=45, resting_hr_baseline=55, training_readiness=99
    )
    result = daily_verdict(
        today, baseline, secondary=secondary, prev_day_below_red=True
    )
    assert result.verdict is Verdict.RED


# --------------------------------------------------------------------------
# evaluate_daily_readiness — orchestration over a mock pool
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_daily_readiness_green_smoke():
    """End-to-end over a mocked pool: green verdict, recommendation persisted."""
    from datetime import date

    pool = AsyncMock()
    pool.fetch = AsyncMock(
        return_value=[{"last_night_avg": v} for v in _SERIES]
    )
    # fetchval order: today HRV, sleep, resting, resting_baseline, TR, yesterday HRV.
    pool.fetchval = AsyncMock(side_effect=[52.0, 85, 50, 50.0, 80, 52.0])
    pool.fetchrow = AsyncMock(return_value={"id": 1, "verdict": "green"})

    result = await evaluate_daily_readiness(pool, user_id=67, day=date(2026, 6, 8))

    assert result.verdict is Verdict.GREEN
    pool.fetchrow.assert_awaited_once()  # persisted exactly one recommendation


@pytest.mark.asyncio
async def test_evaluate_daily_readiness_insufficient_no_baseline():
    """Too few HRV points -> insufficient_baseline; yesterday is not queried."""
    from datetime import date

    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=[{"last_night_avg": 50.0} for _ in range(10)])
    pool.fetchval = AsyncMock(side_effect=[50.0, 85, 50, 50.0, 80])  # no yesterday
    pool.fetchrow = AsyncMock(return_value={"id": 1, "verdict": "insufficient_baseline"})

    result = await evaluate_daily_readiness(
        pool, user_id=67, day=date(2026, 6, 8), persist=False
    )

    assert result.verdict is Verdict.INSUFFICIENT_BASELINE
    pool.fetchrow.assert_not_called()  # persist=False
