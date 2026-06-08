"""HRV-baseline daily readiness (Lot D1) — pure, non-destructive logic.

Implements the validated morning-HRV-versus-baseline rule from spec 03 §1:

    baseline: x = ln(rMSSD) over trailing 60 days (>= 28 points required)
              normal band = [mean - 0.5*sd, mean + 0.5*sd]
    today:    ln(rMSSD_today) >= lower bound  -> GREEN
              < lower bound                   -> AMBER
              < mean - 1.0*sd for 2+ days     -> RED

Everything in this module is a pure function of its inputs (no DB, no I/O) so
the band/hysteresis logic is fully unit-testable. Secondary signals (sleep,
resting HR, Garmin Training Readiness) may only nudge a borderline GREEN to
AMBER — they never override a RED and never trigger a downgrade on their own.
"""

import math
from enum import Enum
from typing import Optional

from pydantic import BaseModel

# Minimum daily HRV points required before a baseline is trustworthy (spec §1).
_MIN_BASELINE_POINTS = 28

# Band half-width (in standard deviations) around the mean ln(rMSSD).
_BAND_HALF_WIDTH_SD = 0.5

# How far below the mean (in SDs) is the deep "RED" threshold.
_RED_THRESHOLD_SD = 1.0

# A GREEN value is only "borderline" (eligible for a secondary nudge) when it
# sits in the lower half of the band, i.e. below the mean but still >= lower.
# This enforces "secondary signals never trigger a downgrade on their own".

# Secondary-modifier trigger thresholds (all flagged non-validated, spec §1).
_SLEEP_SCORE_FLOOR = 50
_RESTING_HR_MARGIN = 5  # bpm above the resting-HR baseline
_TRAINING_READINESS_FLOOR = 30

# AMBER cuts roughly a quarter of the planned session duration.
_AMBER_DURATION_PCT = 75


class Verdict(str, Enum):
    """Daily readiness verdict (string-valued for JSON/DB round-tripping)."""

    GREEN = "green"  # proceed with the planned session
    AMBER = "amber"  # ease: downgrade quality -> easy, or cut ~20-30% duration
    RED = "red"  # rest / active recovery
    INSUFFICIENT_BASELINE = "insufficient_baseline"  # < 28 points -> fall back


class HrvBaseline(BaseModel):
    """Individual ln(rMSSD) baseline rebuilt weekly from trailing daily HRV."""

    mean_ln: float
    sd_ln: float
    n_points: int

    @property
    def lower_ln(self) -> float:
        """Lower bound of the normal band in ln space."""
        return self.mean_ln - _BAND_HALF_WIDTH_SD * self.sd_ln

    @property
    def upper_ln(self) -> float:
        """Upper bound of the normal band in ln space."""
        return self.mean_ln + _BAND_HALF_WIDTH_SD * self.sd_ln

    @property
    def red_threshold_ln(self) -> float:
        """Deep-suppression threshold (mean - 1.0*sd) in ln space."""
        return self.mean_ln - _RED_THRESHOLD_SD * self.sd_ln

    @property
    def low(self) -> float:
        """Lower band bound back in raw rMSSD (ms)."""
        return math.exp(self.lower_ln)

    @property
    def high(self) -> float:
        """Upper band bound back in raw rMSSD (ms)."""
        return math.exp(self.upper_ln)


class SecondaryModifiers(BaseModel):
    """Non-validated secondary signals; may only nudge a borderline GREEN."""

    sleep_score: Optional[float] = None
    resting_hr: Optional[float] = None
    resting_hr_baseline: Optional[float] = None
    training_readiness: Optional[float] = None

    def active_flags(self) -> list[str]:
        """Return the human-readable list of triggered secondary concerns."""
        flags: list[str] = []
        if self.sleep_score is not None and self.sleep_score < _SLEEP_SCORE_FLOOR:
            flags.append(f"sleep_score {self.sleep_score:.0f} < {_SLEEP_SCORE_FLOOR}")
        if (
            self.resting_hr is not None
            and self.resting_hr_baseline is not None
            and self.resting_hr > self.resting_hr_baseline + _RESTING_HR_MARGIN
        ):
            flags.append(
                f"resting HR {self.resting_hr:.0f} > baseline +{_RESTING_HR_MARGIN} bpm"
            )
        if (
            self.training_readiness is not None
            and self.training_readiness < _TRAINING_READINESS_FLOOR
        ):
            flags.append(
                f"training readiness {self.training_readiness:.0f} "
                f"< {_TRAINING_READINESS_FLOOR}"
            )
        return flags


class DailyVerdict(BaseModel):
    """Result of the daily readiness evaluation (persisted + returned by API)."""

    verdict: Verdict
    reason: str
    suggested_modification: dict
    hrv_value: Optional[float] = None
    baseline_low: Optional[float] = None
    baseline_high: Optional[float] = None


def build_hrv_baseline(
    values: list[Optional[float]],
    *,
    min_points: int = _MIN_BASELINE_POINTS,
) -> Optional[HrvBaseline]:
    """Build the ln(rMSSD) baseline from trailing daily HRV values.

    Args:
        values: Daily HRV (rMSSD / overnight average, ms) over the trailing
            window. ``None`` and non-positive entries are ignored (log-undefined).
        min_points: Minimum valid points required (default 28 per spec §1).

    Returns:
        An ``HrvBaseline`` when at least ``min_points`` valid values exist,
        else ``None`` (caller falls back to ``insufficient_baseline``).
    """
    finite = [v for v in values if v is not None and v > 0]
    if len(finite) < min_points:
        return None

    xs = [math.log(v) for v in finite]
    n = len(xs)
    mean = sum(xs) / n
    # Sample standard deviation (n-1) — baseline variability of the individual.
    variance = sum((x - mean) ** 2 for x in xs) / (n - 1)
    sd = math.sqrt(variance)
    return HrvBaseline(mean_ln=mean, sd_ln=sd, n_points=n)


def daily_verdict(
    today_hrv: Optional[float],
    baseline: Optional[HrvBaseline],
    *,
    secondary: Optional[SecondaryModifiers] = None,
    prev_day_below_red: bool = False,
) -> DailyVerdict:
    """Evaluate today's morning HRV against the baseline band (spec §1).

    Args:
        today_hrv: This morning's HRV value (rMSSD / overnight, ms). ``None`` or
            non-positive falls back to ``insufficient_baseline``.
        baseline: The athlete's current baseline, or ``None`` if not enough data.
        secondary: Optional non-validated modifiers (sleep, resting HR, Garmin
            TR). They may only nudge a borderline GREEN down to AMBER.
        prev_day_below_red: Whether yesterday was also below the RED threshold.
            RED requires two consecutive days of deep suppression (hysteresis).

    Returns:
        A ``DailyVerdict`` with the verdict, a human-readable reason, and a
        suggested (non-applied) session modification.
    """
    if baseline is None or today_hrv is None or today_hrv <= 0:
        return DailyVerdict(
            verdict=Verdict.INSUFFICIENT_BASELINE,
            reason=(
                "Not enough HRV history for a reliable baseline — keeping the "
                "planned session unchanged."
            ),
            suggested_modification=_modification(Verdict.INSUFFICIENT_BASELINE),
            hrv_value=today_hrv,
            baseline_low=baseline.low if baseline else None,
            baseline_high=baseline.high if baseline else None,
        )

    today_ln = math.log(today_hrv)
    low, high = baseline.low, baseline.high

    # RED: deep suppression sustained over two consecutive days (hysteresis).
    if today_ln < baseline.red_threshold_ln and prev_day_below_red:
        return DailyVerdict(
            verdict=Verdict.RED,
            reason=(
                f"HRV {today_hrv:.0f} ms well below baseline "
                f"({low:.0f}-{high:.0f} ms) for a second day — rest or active "
                "recovery."
            ),
            suggested_modification=_modification(Verdict.RED),
            hrv_value=today_hrv,
            baseline_low=low,
            baseline_high=high,
        )

    # AMBER: below the lower band bound.
    if today_ln < baseline.lower_ln:
        return DailyVerdict(
            verdict=Verdict.AMBER,
            reason=(
                f"HRV {today_hrv:.0f} ms below the normal band "
                f"({low:.0f}-{high:.0f} ms) — ease today's session."
            ),
            suggested_modification=_modification(Verdict.AMBER),
            hrv_value=today_hrv,
            baseline_low=low,
            baseline_high=high,
        )

    # GREEN, but a borderline value (lower half of the band) plus a secondary
    # concern may be nudged to AMBER. Secondary signals never act on their own.
    flags = secondary.active_flags() if secondary else []
    borderline = today_ln < baseline.mean_ln
    if borderline and flags:
        return DailyVerdict(
            verdict=Verdict.AMBER,
            reason=(
                f"HRV {today_hrv:.0f} ms in range but low, with: "
                f"{'; '.join(flags)} — ease today's session."
            ),
            suggested_modification=_modification(Verdict.AMBER),
            hrv_value=today_hrv,
            baseline_low=low,
            baseline_high=high,
        )

    return DailyVerdict(
        verdict=Verdict.GREEN,
        reason=(
            f"HRV {today_hrv:.0f} ms within baseline ({low:.0f}-{high:.0f} ms) "
            "— proceed with the planned session."
        ),
        suggested_modification=_modification(Verdict.GREEN),
        hrv_value=today_hrv,
        baseline_low=low,
        baseline_high=high,
    )


def _modification(verdict: Verdict) -> dict:
    """Return the suggested (non-applied) session modification for a verdict."""
    if verdict is Verdict.AMBER:
        return {
            "action": "ease",
            "downgrade_quality_to_easy": True,
            "duration_pct": _AMBER_DURATION_PCT,
        }
    if verdict is Verdict.RED:
        return {
            "action": "rest",
            "replace_with": "active_recovery",
            "duration_pct": 0,
        }
    # GREEN and INSUFFICIENT_BASELINE both keep the planned session as-is.
    return {"action": "proceed", "duration_pct": 100}
