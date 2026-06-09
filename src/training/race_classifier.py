"""Trail race classification engine."""

from .models import RaceCategory, RaceFlags


def classify_race(
    distance_km: float,
    elevation_gain_m: int,
    technical_percent: int = 0,
    altitude_max_m: int = 0,
    discipline: str = "trail",
) -> RaceFlags:
    """Classify a race into categories and derive behavior flags.

    Road discipline short-circuits to the road_marathon category: trail-only
    flags (high_dplus, technical, is_ultra, high_altitude) are never set so the
    road path is fully decoupled from trail behaviour.

    Classification by distance (trail):
        trail_court: distance < 42 km
        trail_moyen: 42 <= distance < 80 km
        ultra: 80 <= distance < 160 km
        ultra_longue: distance >= 160 km

    Flags:
        high_dplus: elevation_gain_m / distance_km > 60 (m/km ratio)
        technical: technical_percent > 30
        is_ultra: distance >= 80 km
        high_altitude: altitude_max_m > 2500
        is_road_marathon: discipline == 'road'

    Args:
        distance_km: Race distance in kilometers (positive).
        elevation_gain_m: Total elevation gain in meters (non-negative).
        technical_percent: Percentage of technical terrain (0-100). Defaults to 0.
        altitude_max_m: Maximum altitude in meters (non-negative). Defaults to 0.
        discipline: Race discipline ('trail' | 'road'). Defaults to 'trail'.

    Returns:
        RaceFlags object with category and behavior flags.
    """
    # Road discipline: dedicated category, no trail flags
    if discipline == "road":
        return RaceFlags(
            category=RaceCategory.road_marathon,
            is_road_marathon=True,
        )

    # Determine category based on distance
    if distance_km < 42:
        category = RaceCategory.trail_court
    elif distance_km < 80:
        category = RaceCategory.trail_moyen
    elif distance_km < 160:
        category = RaceCategory.ultra
    else:
        category = RaceCategory.ultra_longue

    # Calculate elevation-to-distance ratio (m/km)
    dplus_per_km = elevation_gain_m / distance_km if distance_km > 0 else 0

    # Determine flags
    high_dplus = dplus_per_km > 60
    technical = technical_percent > 30
    is_ultra = distance_km >= 80
    high_altitude = altitude_max_m > 2500

    return RaceFlags(
        category=category,
        high_dplus=high_dplus,
        technical=technical,
        is_ultra=is_ultra,
        high_altitude=high_altitude,
    )
