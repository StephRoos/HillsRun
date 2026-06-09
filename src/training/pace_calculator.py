"""VMA-driven pace calculator for road-marathon training.

Derives training paces (recovery, easy, marathon, threshold, VO2max) from the
athlete's VMA (maximal aerobic speed) and race objective. When VMA is unknown,
falls back to a VDOT-style estimate from running VO2max (``vma ≈ vo2max / 3.5``).

All paces are pure functions of VMA — nothing is hardcoded. Easy efforts (REC,
EF) are expressed as ranges because they are heart-rate-bound (Z1/Z2); the pace
range only frames the HR target and prevents the classic "easy runs too fast"
marathon error.
"""

from typing import Optional

from pydantic import BaseModel

from .models import RaceObjective

# Marathon-pace fraction of VMA per objective (see spec §4).
_PCT_MARATHON: dict[RaceObjective, float] = {
    RaceObjective.finish: 0.78,
    RaceObjective.midpack: 0.80,
    RaceObjective.performance: 0.83,
}

# Fixed %VMA fractions for the structured zones.
_PCT_TMP = 0.88  # Z3-Z4 threshold
_PCT_INT = 1.00  # Z5 VO2max reps

# %VMA ranges for the heart-rate-bound easy efforts (low speed, high speed).
_PCT_REC = (0.63, 0.67)  # Z1-Z2 recovery
_PCT_EF = (0.68, 0.72)  # Z2 easy

# Marathon distance in km (used for the target-time projection).
_MARATHON_KM = 42.195

# VDOT-style conversion from running VO2max to VMA in km/h.
_VO2MAX_TO_VMA = 3.5

# An objective target faster than the VMA prediction by more than this margin is
# flagged optimistic (non-blocking).
_OPTIMISTIC_MARGIN = 0.02


def _sec_per_km(kmh: float) -> int:
    """Convert a speed in km/h to a pace in integer seconds per km.

    Args:
        kmh: Speed in kilometres per hour.

    Returns:
        Pace in seconds per kilometre, rounded to the nearest second.
    """
    return round(3600.0 / kmh)


def format_pace(sec_per_km: int) -> str:
    """Format a pace in seconds per km as ``m:ss``.

    Args:
        sec_per_km: Pace in seconds per kilometre.

    Returns:
        Pace string such as ``"4:59"``.
    """
    minutes, seconds = divmod(int(round(sec_per_km)), 60)
    return f"{minutes}:{seconds:02d}"


class PaceZone(BaseModel):
    """A single training pace (or pace range) derived from VMA.

    For structured zones (MPR, TMP, INT) the low and high bounds are equal. For
    heart-rate-bound easy efforts (REC, EF) the bounds frame a range: ``*_slow``
    corresponds to the lower speed, ``*_fast`` to the higher speed.
    """

    zone: str  # SessionType code: REC | EF | MPR | TMP | INT
    pct_vma_low: float
    pct_vma_high: float
    kmh_low: float  # slower bound (lower %VMA)
    kmh_high: float  # faster bound (higher %VMA)
    sec_per_km_slow: int  # pace at kmh_low (slower)
    sec_per_km_fast: int  # pace at kmh_high (faster)

    @property
    def is_range(self) -> bool:
        """Whether this zone is a true range (easy efforts) vs a single pace."""
        return self.sec_per_km_slow != self.sec_per_km_fast

    @property
    def label(self) -> str:
        """Human-readable pace, e.g. ``"6:34–6:11 /km"`` or ``"4:59 /km"``."""
        if self.is_range:
            return f"{format_pace(self.sec_per_km_slow)}–{format_pace(self.sec_per_km_fast)} /km"
        return f"{format_pace(self.sec_per_km_fast)} /km"


class PaceSet(BaseModel):
    """Full set of training paces for an athlete, keyed by zone code."""

    vma_kmh: float
    objective: RaceObjective
    pct_marathon: float
    pace_source: str  # "vma" | "vo2max_estimate"
    target_time_seconds: int  # projected marathon time at MPR pace
    pace_objective_optimistic: bool = False
    zones: dict[str, PaceZone]

    def pace_for(self, session_code: str) -> Optional[PaceZone]:
        """Return the pace zone for a session-type code, or None if absent.

        Threshold/interval sessions reuse the TMP/INT zones; long runs and
        endurance reuse EF.

        Args:
            session_code: SessionType code (e.g. ``"MPR"``, ``"EF"``).

        Returns:
            The matching :class:`PaceZone`, or ``None`` when unmapped.
        """
        return self.zones.get(session_code)


def _build_range_zone(code: str, vma_kmh: float, pct: tuple[float, float]) -> PaceZone:
    """Build a ranged easy-effort zone (REC/EF) from a %VMA tuple."""
    kmh_low = vma_kmh * pct[0]
    kmh_high = vma_kmh * pct[1]
    return PaceZone(
        zone=code,
        pct_vma_low=pct[0],
        pct_vma_high=pct[1],
        kmh_low=kmh_low,
        kmh_high=kmh_high,
        sec_per_km_slow=_sec_per_km(kmh_low),
        sec_per_km_fast=_sec_per_km(kmh_high),
    )


def _build_point_zone(code: str, vma_kmh: float, pct: float) -> PaceZone:
    """Build a single-pace zone (MPR/TMP/INT) from a %VMA fraction."""
    kmh = vma_kmh * pct
    sec = _sec_per_km(kmh)
    return PaceZone(
        zone=code,
        pct_vma_low=pct,
        pct_vma_high=pct,
        kmh_low=kmh,
        kmh_high=kmh,
        sec_per_km_slow=sec,
        sec_per_km_fast=sec,
    )


def compute_paces(
    vma_kmh: float,
    objective: RaceObjective = RaceObjective.finish,
    target_time_seconds: Optional[int] = None,
    pace_source: str = "vma",
) -> PaceSet:
    """Compute the full set of training paces from VMA and race objective.

    Args:
        vma_kmh: Maximal aerobic speed in km/h (must be > 0).
        objective: Race objective driving the marathon-pace fraction of VMA.
        target_time_seconds: Optional goal marathon time. If the goal pace is
            faster than the VMA prediction by more than ~2%, the result is
            flagged ``pace_objective_optimistic`` (non-blocking).
        pace_source: Provenance tag for the plan's generation params; set to
            ``"vo2max_estimate"`` when VMA was derived from VO2max.

    Returns:
        A :class:`PaceSet` with REC/EF (ranges) and MPR/TMP/INT (single paces),
        a projected marathon time, and the optimistic flag.

    Raises:
        ValueError: If ``vma_kmh`` is not positive.
    """
    if vma_kmh <= 0:
        raise ValueError("vma_kmh must be positive")

    pct_marathon = _PCT_MARATHON[objective]

    zones = {
        "REC": _build_range_zone("REC", vma_kmh, _PCT_REC),
        "EF": _build_range_zone("EF", vma_kmh, _PCT_EF),
        "MPR": _build_point_zone("MPR", vma_kmh, pct_marathon),
        "TMP": _build_point_zone("TMP", vma_kmh, _PCT_TMP),
        "INT": _build_point_zone("INT", vma_kmh, _PCT_INT),
    }

    # Projected marathon time at marathon pace.
    mpr_sec_per_km = zones["MPR"].sec_per_km_fast
    target_time = round(mpr_sec_per_km * _MARATHON_KM)

    # Flag an overly ambitious goal time (required pace faster than predicted).
    optimistic = False
    if target_time_seconds is not None:
        required_sec_per_km = target_time_seconds / _MARATHON_KM
        if required_sec_per_km < mpr_sec_per_km * (1.0 - _OPTIMISTIC_MARGIN):
            optimistic = True

    return PaceSet(
        vma_kmh=vma_kmh,
        objective=objective,
        pct_marathon=pct_marathon,
        pace_source=pace_source,
        target_time_seconds=target_time,
        pace_objective_optimistic=optimistic,
        zones=zones,
    )


def compute_paces_from_fitness(
    vma_kmh: Optional[float],
    vo2_max: Optional[float] = None,
    objective: RaceObjective = RaceObjective.finish,
    target_time_seconds: Optional[int] = None,
) -> PaceSet:
    """Compute paces from VMA, falling back to a VO2max (VDOT) estimate.

    Mirrors the plan generator's data availability: when ``vma_kmh`` is present
    it is used directly; otherwise VMA is estimated from running VO2max
    (``vma ≈ vo2max / 3.5``) and the result is tagged ``vo2max_estimate``.

    Args:
        vma_kmh: Measured/manual VMA in km/h, or ``None``.
        vo2_max: Running VO2max in ml/kg/min, used only when ``vma_kmh`` is None.
        objective: Race objective driving the marathon-pace fraction of VMA.
        target_time_seconds: Optional goal marathon time (see ``compute_paces``).

    Returns:
        A :class:`PaceSet` derived from VMA or its VO2max estimate.

    Raises:
        ValueError: If neither a positive VMA nor a positive VO2max is available.
    """
    if vma_kmh is not None and vma_kmh > 0:
        return compute_paces(
            vma_kmh,
            objective=objective,
            target_time_seconds=target_time_seconds,
            pace_source="vma",
        )

    if vo2_max is not None and vo2_max > 0:
        estimated_vma = vo2_max / _VO2MAX_TO_VMA
        return compute_paces(
            estimated_vma,
            objective=objective,
            target_time_seconds=target_time_seconds,
            pace_source="vo2max_estimate",
        )

    raise ValueError("Cannot compute paces: no VMA and no VO2max available")
