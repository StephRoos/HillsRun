"""Utility functions for the HillsRun Dashboard."""

from typing import Optional

# Mapping Garmin aerobic_training_effect (0-5 scale) to approximate TSS.
# TE 0-1: recovery (~10-20 TSS), TE 2: maintaining (~40), TE 3: improving (~70),
# TE 4: highly improving (~110), TE 5: overreaching (~160+).
# We scale with duration to account for long easy vs short hard sessions.
_TE_TSS_BASE = {0: 0, 1: 20, 2: 40, 3: 70, 4: 110, 5: 160}


def te_to_tss(training_effect: float, duration_seconds: float) -> float:
    """Convert Garmin aerobic_training_effect to estimated TSS.

    Uses TE as intensity proxy, scaled by duration relative to 1 hour.
    """
    if not training_effect or not duration_seconds:
        return 0.0

    # Linear interpolation between TE breakpoints
    te = max(0.0, min(training_effect, 5.0))
    te_low = int(te)
    te_high = min(te_low + 1, 5)
    frac = te - te_low
    base_tss = _TE_TSS_BASE[te_low] * (1 - frac) + _TE_TSS_BASE[te_high] * frac

    # Scale by duration (1h = baseline, 2h = ~2x, 30min = ~0.5x)
    duration_factor = duration_seconds / 3600.0
    return round(base_tss * duration_factor, 1)


def get_tss(activity: dict) -> float:
    """Get TSS for an activity.

    Priority: Garmin TSS > TE-based estimate.
    """
    tss = activity.get("training_stress_score")
    if tss:
        return float(tss)

    te = activity.get("aerobic_training_effect")
    duration = activity.get("duration_seconds")
    if te and duration:
        return te_to_tss(te, duration)

    return 0.0


def format_duration(seconds: Optional[float]) -> str:
    """Format seconds into 'Xh Ym' or 'Xm Ys'."""
    if not seconds:
        return "—"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m {secs:02d}s"


def format_pace(speed_m_s: Optional[float]) -> str:
    """Convert speed (m/s) to pace (min/km)."""
    if not speed_m_s or speed_m_s <= 0:
        return "—"
    pace_s_per_km = 1000.0 / speed_m_s
    minutes = int(pace_s_per_km // 60)
    secs = int(pace_s_per_km % 60)
    return f"{minutes}:{secs:02d} /km"


SPORT_ICONS = {
    "running": "\U0001f3c3",
    "cycling": "\U0001f6b4",
    "swimming": "\U0001f3ca",
    "trail_running": "\u26f0\ufe0f",
    "hiking": "\U0001f6b6",
    "walking": "\U0001f6b6",
    "strength_training": "\U0001f4aa",
    "yoga": "\U0001f9d8",
    "multi_sport": "\U0001f3c5",
}


def sport_icon(sport_type: Optional[str]) -> str:
    """Return an emoji for the given sport type."""
    if not sport_type:
        return "\U0001f3c3"
    return SPORT_ICONS.get(sport_type.lower(), "\U0001f3c3")


