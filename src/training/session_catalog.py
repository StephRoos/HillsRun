"""Static catalog of session templates for trail running training plans."""

from pydantic import BaseModel

from .models import ExperienceLevel, Intensity, PlanPhase, SessionType, WorkoutBlock


class SessionTemplate(BaseModel):
    """Template for a training session with configurable details."""

    session_type: SessionType
    title: str
    description: str
    sport_type: str = "trail_running"
    intensity: Intensity
    hr_zone_primary: int
    duration_range_minutes: tuple[int, int]
    blocks: list[WorkoutBlock]


def get_session_template(
    session_type: SessionType, experience: ExperienceLevel, phase: PlanPhase
) -> SessionTemplate:
    """
    Retrieve a session template adapted to experience level and training phase.

    Args:
        session_type: Type of training session (EF, SL, TMP, etc.)
        experience: Athlete experience level (beginner, intermediate, advanced, expert)
        phase: Training periodization phase (base, development, specific, taper)

    Returns:
        SessionTemplate configured for the given parameters

    Raises:
        ValueError: If session_type is invalid
    """
    catalog = _build_catalog()
    key = (session_type, experience, phase)

    if key not in catalog:
        raise ValueError(f"No template found for {session_type.value} at {experience.value} level in {phase.value} phase")

    return catalog[key]


def get_phase_session_types(phase: PlanPhase, experience: ExperienceLevel) -> list[SessionType]:
    """
    Get recommended session types for a specific training phase and experience level.

    Args:
        phase: Training periodization phase
        experience: Athlete experience level

    Returns:
        List of recommended SessionType values for this phase and level
    """
    base_sessions = {
        PlanPhase.base: [SessionType.EF, SessionType.SL, SessionType.REC, SessionType.RMU],
        PlanPhase.development: [SessionType.EF, SessionType.SL, SessionType.TMP, SessionType.INT, SessionType.REC, SessionType.RMU],
        PlanPhase.specific: [SessionType.EF, SessionType.SL, SessionType.TMP, SessionType.INT, SessionType.COT, SessionType.DESC, SessionType.REC],
        PlanPhase.taper: [SessionType.EF, SessionType.SL, SessionType.REC],
    }

    recommendations = base_sessions[phase].copy()

    if phase == PlanPhase.base and experience in (ExperienceLevel.advanced, ExperienceLevel.expert):
        recommendations.insert(3, SessionType.COT)

    if phase == PlanPhase.development:
        if SessionType.COT not in recommendations:
            recommendations.insert(4, SessionType.COT)

    if phase == PlanPhase.specific and experience in (ExperienceLevel.advanced, ExperienceLevel.expert):
        recommendations.append(SessionType.RMU)

    if phase == PlanPhase.taper and experience in (ExperienceLevel.advanced, ExperienceLevel.expert):
        recommendations.insert(1, SessionType.TMP)

    return recommendations


def _build_catalog() -> dict:
    """
    Build the complete session template catalog.

    Returns:
        Dictionary keyed by (SessionType, ExperienceLevel, PlanPhase) tuples
    """
    catalog = {}

    # EF - Endurance Fondamentale
    for phase in PlanPhase:
        for experience in ExperienceLevel:
            duration_range = _get_duration_range(SessionType.EF, experience)
            catalog[(SessionType.EF, experience, phase)] = SessionTemplate(
                session_type=SessionType.EF,
                title="Endurance Fondamentale",
                description="Easy aerobic run to build base fitness and active recovery",
                sport_type="trail_running",
                intensity=Intensity.easy,
                hr_zone_primary=2,
                duration_range_minutes=duration_range,
                blocks=[
                    WorkoutBlock(name="Warmup", duration_seconds=600, hr_zone=1, description="Easy jog Z1"),
                    WorkoutBlock(name="Main", duration_seconds=(duration_range[0] - 5) * 60, hr_zone=2, description="Steady Z2"),
                    WorkoutBlock(name="Cooldown", duration_seconds=300, hr_zone=1, description="Easy jog Z1"),
                ],
            )

    # SL - Sortie Longue
    for phase in PlanPhase:
        for experience in ExperienceLevel:
            duration_range = _get_duration_range(SessionType.SL, experience)
            main_duration = max(0, (duration_range[0] - 5) * 60)
            blocks = [
                WorkoutBlock(name="Warmup", duration_seconds=900, hr_zone=1, description="Easy jog Z1"),
                WorkoutBlock(
                    name="Main",
                    duration_seconds=main_duration,
                    hr_zone=2,
                    description="Long run Z2 with Z3 surges in development/specific phases" if phase in (PlanPhase.development, PlanPhase.specific) else "Long run Z2",
                ),
                WorkoutBlock(name="Cooldown", duration_seconds=600, hr_zone=1, description="Easy jog Z1"),
            ]
            catalog[(SessionType.SL, experience, phase)] = SessionTemplate(
                session_type=SessionType.SL,
                title="Sortie Longue",
                description="Long run to build aerobic capacity and trail-specific endurance",
                sport_type="trail_running",
                intensity=Intensity.moderate,
                hr_zone_primary=2,
                duration_range_minutes=duration_range,
                blocks=blocks,
            )

    # TMP - Tempo
    for phase in PlanPhase:
        for experience in ExperienceLevel:
            duration_range = _get_duration_range(SessionType.TMP, experience)
            tempo_duration = int((duration_range[0] + 10) * 60)
            catalog[(SessionType.TMP, experience, phase)] = SessionTemplate(
                session_type=SessionType.TMP,
                title="Tempo",
                description="Sustained threshold effort to improve lactate clearance",
                sport_type="trail_running",
                intensity=Intensity.hard,
                hr_zone_primary=3,
                duration_range_minutes=duration_range,
                blocks=[
                    WorkoutBlock(name="Warmup", duration_seconds=900, hr_zone=2, description="Z1-Z2 progressive warmup"),
                    WorkoutBlock(name="Tempo", duration_seconds=tempo_duration, hr_zone=3, description="Steady Z3"),
                    WorkoutBlock(name="Cooldown", duration_seconds=600, hr_zone=1, description="Easy jog Z1"),
                ],
            )

    # INT - Intervalles
    for phase in PlanPhase:
        for experience in ExperienceLevel:
            duration_range = _get_duration_range(SessionType.INT, experience)
            num_intervals = 8 if experience == ExperienceLevel.beginner else (10 if experience in (ExperienceLevel.intermediate, ExperienceLevel.advanced) else 12)
            interval_duration = 180 if experience == ExperienceLevel.beginner else 240
            catalog[(SessionType.INT, experience, phase)] = SessionTemplate(
                session_type=SessionType.INT,
                title="Intervalles",
                description="High-intensity repeats to develop VO2max and anaerobic capacity",
                sport_type="trail_running",
                intensity=Intensity.hard,
                hr_zone_primary=4,
                duration_range_minutes=duration_range,
                blocks=[
                    WorkoutBlock(name="Warmup", duration_seconds=900, hr_zone=2, description="Z1-Z2 progressive warmup"),
                    WorkoutBlock(
                        name="Intervals",
                        duration_seconds=num_intervals * (interval_duration + 60),
                        hr_zone=4,
                        description=f"{num_intervals} × {interval_duration // 60}min Z4 / 1min recovery Z1",
                    ),
                    WorkoutBlock(name="Cooldown", duration_seconds=600, hr_zone=1, description="Easy jog Z1"),
                ],
            )

    # COT - Cotes
    for phase in PlanPhase:
        for experience in ExperienceLevel:
            duration_range = _get_duration_range(SessionType.COT, experience)
            num_reps = 6 if experience == ExperienceLevel.beginner else (8 if experience in (ExperienceLevel.intermediate, ExperienceLevel.advanced) else 10)
            catalog[(SessionType.COT, experience, phase)] = SessionTemplate(
                session_type=SessionType.COT,
                title="Cotes",
                description="Hill repeats to build leg strength and anaerobic power",
                sport_type="trail_running",
                intensity=Intensity.hard,
                hr_zone_primary=3,
                duration_range_minutes=duration_range,
                blocks=[
                    WorkoutBlock(name="Warmup", duration_seconds=900, hr_zone=2, description="Jog uphill Z2"),
                    WorkoutBlock(
                        name="Hill Repeats",
                        duration_seconds=num_reps * (150 + 120),
                        hr_zone=3,
                        description=f"{num_reps} × 2-3min uphill Z3-Z4 / jog down Z1",
                    ),
                    WorkoutBlock(name="Cooldown", duration_seconds=600, hr_zone=1, description="Easy jog Z1"),
                ],
            )

    # DESC - Descente
    for phase in PlanPhase:
        for experience in ExperienceLevel:
            catalog[(SessionType.DESC, experience, phase)] = SessionTemplate(
                session_type=SessionType.DESC,
                title="Descente Technique",
                description="Technical downhill running to improve skills and leg control",
                sport_type="trail_running",
                intensity=Intensity.moderate,
                hr_zone_primary=2,
                duration_range_minutes=(30, 45),
                blocks=[
                    WorkoutBlock(name="Warmup", duration_seconds=600, hr_zone=2, description="Jog flat terrain Z2"),
                    WorkoutBlock(name="Technical Downhill Drills", duration_seconds=1800, hr_zone=2, description="Controlled technical descents Z2"),
                    WorkoutBlock(name="Cooldown", duration_seconds=300, hr_zone=1, description="Easy jog Z1"),
                ],
            )

    # REC - Recuperation
    for phase in PlanPhase:
        for experience in ExperienceLevel:
            catalog[(SessionType.REC, experience, phase)] = SessionTemplate(
                session_type=SessionType.REC,
                title="Récupération",
                description="Easy recovery jog to promote blood flow and adaptation",
                sport_type="trail_running",
                intensity=Intensity.easy,
                hr_zone_primary=1,
                duration_range_minutes=(20, 30),
                blocks=[
                    WorkoutBlock(name="Easy Jog", duration_seconds=1500, hr_zone=1, description="Conversational pace Z1"),
                ],
            )

    # RMU - Renforcement Musculaire
    for phase in PlanPhase:
        for experience in ExperienceLevel:
            catalog[(SessionType.RMU, experience, phase)] = SessionTemplate(
                session_type=SessionType.RMU,
                title="Renforcement Musculaire",
                description="Strength and power circuit for injury prevention and performance",
                sport_type="strength_training",
                intensity=Intensity.moderate,
                hr_zone_primary=2,
                duration_range_minutes=(30, 45),
                blocks=[
                    WorkoutBlock(name="Warmup", duration_seconds=600, hr_zone=1, description="Dynamic stretching and mobility Z1"),
                    WorkoutBlock(
                        name="Strength Circuit",
                        duration_seconds=1800,
                        description="Squats, lunges, core, plyometrics (3-4 sets × 8-12 reps)",
                    ),
                    WorkoutBlock(name="Cooldown", duration_seconds=300, description="Static stretching and recovery"),
                ],
            )

    # REST - Rest day
    for phase in PlanPhase:
        for experience in ExperienceLevel:
            catalog[(SessionType.REST, experience, phase)] = SessionTemplate(
                session_type=SessionType.REST,
                title="Jour de Repos",
                description="Complete rest day for recovery and adaptation",
                sport_type="trail_running",
                intensity=Intensity.easy,
                hr_zone_primary=1,
                duration_range_minutes=(0, 0),
                blocks=[],
            )

    return catalog


def _get_duration_range(session_type: SessionType, experience: ExperienceLevel) -> tuple[int, int]:
    """
    Get the duration range in minutes for a session type and experience level.

    Args:
        session_type: Type of training session
        experience: Athlete experience level

    Returns:
        Tuple of (min_duration, max_duration) in minutes
    """
    ranges = {
        SessionType.EF: {
            ExperienceLevel.beginner: (30, 45),
            ExperienceLevel.intermediate: (40, 60),
            ExperienceLevel.advanced: (50, 75),
            ExperienceLevel.expert: (60, 90),
        },
        SessionType.SL: {
            ExperienceLevel.beginner: (60, 90),
            ExperienceLevel.intermediate: (75, 120),
            ExperienceLevel.advanced: (90, 150),
            ExperienceLevel.expert: (120, 180),
        },
        SessionType.TMP: {
            ExperienceLevel.beginner: (30, 40),
            ExperienceLevel.intermediate: (35, 50),
            ExperienceLevel.advanced: (40, 60),
            ExperienceLevel.expert: (45, 70),
        },
        SessionType.INT: {
            ExperienceLevel.beginner: (30, 40),
            ExperienceLevel.intermediate: (35, 50),
            ExperienceLevel.advanced: (45, 60),
            ExperienceLevel.expert: (50, 70),
        },
        SessionType.COT: {
            ExperienceLevel.beginner: (30, 40),
            ExperienceLevel.intermediate: (35, 50),
            ExperienceLevel.advanced: (40, 60),
            ExperienceLevel.expert: (50, 70),
        },
        SessionType.DESC: {
            ExperienceLevel.beginner: (30, 45),
            ExperienceLevel.intermediate: (30, 45),
            ExperienceLevel.advanced: (30, 45),
            ExperienceLevel.expert: (30, 45),
        },
        SessionType.REC: {
            ExperienceLevel.beginner: (20, 30),
            ExperienceLevel.intermediate: (20, 30),
            ExperienceLevel.advanced: (20, 30),
            ExperienceLevel.expert: (20, 30),
        },
        SessionType.RMU: {
            ExperienceLevel.beginner: (30, 45),
            ExperienceLevel.intermediate: (30, 45),
            ExperienceLevel.advanced: (30, 45),
            ExperienceLevel.expert: (30, 45),
        },
        SessionType.REST: {
            ExperienceLevel.beginner: (0, 0),
            ExperienceLevel.intermediate: (0, 0),
            ExperienceLevel.advanced: (0, 0),
            ExperienceLevel.expert: (0, 0),
        },
    }
    return ranges[session_type][experience]
