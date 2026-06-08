"""Heart rate zone calculator using the Karvonen formula."""

from typing import Optional

from .models import HRZone, SessionType


def estimate_max_hr(age: int) -> int:
    """Estimate maximum heart rate using 220 - age formula.

    Args:
        age: Athlete age in years.

    Returns:
        Estimated maximum heart rate in bpm.
    """
    return 220 - age


def calculate_hr_zones(
    fc_max: Optional[int] = None,
    fc_repos: Optional[int] = None,
    age: Optional[int] = None,
) -> list[HRZone]:
    """Calculate heart rate training zones using the Karvonen formula.

    If fc_max is not provided, estimates it from age (220 - age).
    If fc_repos is not provided, defaults to 60 bpm.

    Zones:
        Z1: Recovery (50-60% HRR)
        Z2: Endurance (60-70% HRR)
        Z3: Tempo (70-80% HRR)
        Z4: Threshold (80-90% HRR)
        Z5: VO2max (90-100% HRR)

    Formula: target = fc_repos + (HRR × percentage)
    where HRR = fc_max - fc_repos

    Args:
        fc_max: Maximum heart rate in bpm. If None, estimates from age.
        fc_repos: Resting heart rate in bpm. Defaults to 60 if None.
        age: Athlete age in years. Used to estimate fc_max if not provided.

    Returns:
        List of HRZone objects for zones 1-5.

    Raises:
        ValueError: If fc_max cannot be determined (both fc_max and age are None).
    """
    if fc_max is None:
        if age is None:
            raise ValueError("Either fc_max or age must be provided")
        fc_max = estimate_max_hr(age)

    if fc_repos is None:
        fc_repos = 60

    hrr = fc_max - fc_repos

    zone_definitions = [
        {
            "zone": 1,
            "name": "Z1 Recovery",
            "percent_min": 0.50,
            "percent_max": 0.60,
            "description": "Active recovery and aerobic base building",
        },
        {
            "zone": 2,
            "name": "Z2 Endurance",
            "percent_min": 0.60,
            "percent_max": 0.70,
            "description": "Long, steady efforts and aerobic capacity",
        },
        {
            "zone": 3,
            "name": "Z3 Tempo",
            "percent_min": 0.70,
            "percent_max": 0.80,
            "description": "Sustained threshold efforts",
        },
        {
            "zone": 4,
            "name": "Z4 Threshold",
            "percent_min": 0.80,
            "percent_max": 0.90,
            "description": "Lactate threshold and anaerobic capacity",
        },
        {
            "zone": 5,
            "name": "Z5 VO2max",
            "percent_min": 0.90,
            "percent_max": 1.00,
            "description": "Maximum aerobic power and VO2max",
        },
    ]

    zones = []
    for zone_def in zone_definitions:
        hr_min = int(fc_repos + (hrr * zone_def["percent_min"]))
        hr_max = int(fc_repos + (hrr * zone_def["percent_max"]))

        zone = HRZone(
            zone=zone_def["zone"],
            name=zone_def["name"],
            hr_min=hr_min,
            hr_max=hr_max,
            description=zone_def["description"],
        )
        zones.append(zone)

    return zones


def get_zone_for_session_type(session_type: SessionType) -> int:
    """Get recommended heart rate zone for a session type.

    Mapping:
        REST, REC → Z1
        EF, SL, DESC, RMU → Z2
        TMP, COT, MPR → Z3
        INT → Z4

    Args:
        session_type: The training session type.

    Returns:
        Recommended heart rate zone (1-5).
    """
    zone_mapping: dict[SessionType, int] = {
        SessionType.REST: 1,
        SessionType.REC: 1,
        SessionType.EF: 2,
        SessionType.SL: 2,
        SessionType.DESC: 2,
        SessionType.RMU: 2,
        SessionType.TMP: 3,
        SessionType.COT: 3,
        SessionType.MPR: 3,
        SessionType.INT: 4,
    }

    return zone_mapping.get(session_type, 2)
