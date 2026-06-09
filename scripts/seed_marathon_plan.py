"""Seed the road-marathon athlete profile and generate the real plan (Lot 7).

This script wires the locked athlete profile from
``specs/02-road-marathon-adaptation.md`` (§2) into the database, generates the
Marathon de Brugge training plan with the road-marathon engine, and exports a
human-readable, week-by-week markdown report to ``specs/mon-plan-marathon.md``.

The script is **idempotent**: re-running upserts the profile, reuses the
existing race target, deletes any plan previously generated for that race, and
regenerates a single fresh plan. DB credentials are read from the environment
(never committed).

Usage::

    uv run python scripts/seed_marathon_plan.py [--user-id N] [--out PATH]

Environment: ``POSTGRES_HOST``, ``POSTGRES_PORT``, ``POSTGRES_DB``,
``POSTGRES_USER``, ``POSTGRES_PASSWORD``, ``POSTGRES_SSL`` (same as the API).
``SEED_GARMIN_USER_ID`` may set the target user when ``--user-id`` is omitted.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DatabaseConfig
from src.database import Database
from src.training import db_operations as db_ops
from src.training.models import GeneratePlanRequest
from src.training.pace_calculator import PaceSet
from src.training.plan_generator import generate_plan

# --- Locked profile / race (spec §2) --------------------------------------

TARGET_VMA = 14.5
RACE_NAME = "Marathon de Brugge"
RACE_DATE = date(2026, 10, 12)
TARGET_TIME_SECONDS = 12600  # 3h30

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "specs" / "mon-plan-marathon.md"
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_env_file(path: Path = _ENV_FILE) -> None:
    """Load ``KEY=VALUE`` pairs from a ``.env`` file into ``os.environ``.

    The project ships no python-dotenv dependency, so this is a minimal, zero-dep
    parser. Existing environment variables always win — values from the file only
    fill in what is not already set, so an explicit ``export`` still overrides it.

    Args:
        path: Path to the ``.env`` file. Silently does nothing if absent.
    """
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

PROFILE_DATA: dict[str, Any] = {
    "experience_level": "intermediate",
    "fc_max": 188,
    "fc_repos": 56,
    "available_days_per_week": 4,
    "has_gym_access": False,
    "day_preferences": {"long_run": 7, "quality": [4], "strength": 3},
}

RACE_DATA: dict[str, Any] = {
    "race_name": RACE_NAME,
    "race_date": RACE_DATE,
    "distance_km": 42.195,
    "elevation_gain_m": 0,
    "elevation_loss_m": 0,
    "technical_percent": 0,
    "altitude_max_m": 0,
    "objective": "performance",
    "discipline": "road",
    "target_time_seconds": TARGET_TIME_SECONDS,
}

# Session-type code -> pace zone code used for the markdown pace column.
_SESSION_PACE_CODE = {
    "EF": "EF",
    "SL": "EF",
    "REC": "REC",
    "MPR": "MPR",
    "TMP": "TMP",
    "INT": "INT",
}

_DAY_NAMES = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday",
}


def _db_config_from_env() -> DatabaseConfig:
    """Build a :class:`DatabaseConfig` from environment variables.

    Mirrors ``src.api.main._db_config_from_env`` so the script connects exactly
    like the running API.

    Returns:
        Database configuration populated from ``POSTGRES_*`` env vars.
    """
    return DatabaseConfig(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ.get("POSTGRES_DB", "garmin_connect"),
        user=os.environ.get("POSTGRES_USER", "garmin"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
        ssl=os.environ.get("POSTGRES_SSL", "false").lower() in ("true", "1", "yes"),
    )


async def resolve_user_id(pool, explicit: Optional[int]) -> int:
    """Resolve the garmin user_id to seed.

    Priority: explicit CLI value > ``SEED_GARMIN_USER_ID`` env > the sole row in
    ``garmin_user`` when exactly one exists.

    Args:
        pool: asyncpg connection pool.
        explicit: Optional user_id passed on the command line.

    Returns:
        The resolved garmin user_id.

    Raises:
        ValueError: If the user cannot be resolved unambiguously.
    """
    if explicit is not None:
        return explicit

    env_val = os.environ.get("SEED_GARMIN_USER_ID")
    if env_val:
        return int(env_val)

    rows = await pool.fetch("SELECT user_id FROM garmin_user ORDER BY user_id ASC")
    ids = [r["user_id"] for r in rows]
    if len(ids) == 1:
        return ids[0]
    raise ValueError(
        "Cannot resolve garmin user_id automatically "
        f"(found {len(ids)}: {ids}). Pass --user-id or set SEED_GARMIN_USER_ID."
    )


async def set_manual_vma(pool, user_id: int, vma: float) -> None:
    """Set ``garmin_user.manual_vma`` for the athlete.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.
        vma: VMA in km/h to store.

    Raises:
        ValueError: If no ``garmin_user`` row exists for ``user_id``.
    """
    row = await pool.fetchrow(
        "UPDATE garmin_user SET manual_vma = $1 WHERE user_id = $2 RETURNING user_id",
        vma,
        user_id,
    )
    if row is None:
        raise ValueError(
            f"No garmin_user row for user_id={user_id}; cannot set manual_vma."
        )


async def find_or_create_race(pool, user_id: int) -> dict[str, Any]:
    """Return the Brugge race target, creating it once if absent (idempotent).

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.

    Returns:
        The race target dict.
    """
    existing = await db_ops.list_race_targets(pool, user_id)
    for race in existing:
        if race.get("race_name") == RACE_NAME and race.get("race_date") == RACE_DATE:
            return race
    return await db_ops.create_race_target(pool, user_id, RACE_DATA)


async def delete_existing_plans(pool, user_id: int, race_target_id: int) -> int:
    """Delete plans previously generated for this race target (idempotency).

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID.
        race_target_id: Race target whose plans should be cleared.

    Returns:
        Number of plans deleted.
    """
    plans, _ = await db_ops.list_training_plans(pool, user_id, limit=200)
    deleted = 0
    for plan in plans:
        if plan.get("race_target_id") == race_target_id:
            if await db_ops.delete_training_plan(pool, plan["id"], user_id):
                deleted += 1
    return deleted


def _fmt_duration(seconds: Optional[int]) -> str:
    """Format a duration in seconds as ``Hh MMm`` / ``MMm``.

    Args:
        seconds: Duration in seconds, or None.

    Returns:
        Human-readable duration, or ``"—"`` when missing.
    """
    if not seconds:
        return "—"
    minutes = int(round(seconds / 60))
    hours, mins = divmod(minutes, 60)
    if hours:
        return f"{hours}h{mins:02d}"
    return f"{mins}min"


def _fmt_distance(meters: Optional[float]) -> str:
    """Format a distance in metres as kilometres.

    Args:
        meters: Distance in metres, or None.

    Returns:
        Distance like ``"29.5 km"``, or ``"—"`` when missing.
    """
    if not meters:
        return "—"
    return f"{meters / 1000:.1f} km"


def _session_pace_label(session_type: str, paces: Optional[PaceSet]) -> str:
    """Return the pace label for a session, or ``"—"`` when not pace-bound.

    Args:
        session_type: SessionType code (e.g. ``"MPR"``).
        paces: The plan's PaceSet, or None for trail/single-pace plans.

    Returns:
        A pace label like ``"4:59 /km"`` or ``"—"``.
    """
    if paces is None:
        return "—"
    code = _SESSION_PACE_CODE.get(session_type)
    if code is None:
        return "—"
    zone = paces.pace_for(code)
    return zone.label if zone else "—"


def _mp_finish_block(session: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Return the marathon-pace finish block of a session, if any.

    The long run carries its structure in ``blocks`` (stored as JSON, returned
    by asyncpg as a string or a list). The marathon-pace block is the Z3 one.

    Args:
        session: A planned-workout row.

    Returns:
        The MP block dict (name/duration_seconds/hr_zone/description), or None.
    """
    blocks = session.get("blocks")
    if isinstance(blocks, str):
        try:
            blocks = json.loads(blocks)
        except (ValueError, TypeError):
            return None
    if not blocks:
        return None
    for block in blocks:
        if isinstance(block, dict) and block.get("hr_zone") == 3:
            return block
    return None


def _session_pace_cell(
    session: dict[str, Any], session_type: str, paces: Optional[PaceSet]
) -> str:
    """Pace label for a session row, surfacing a long-run MP finish block.

    Args:
        session: The planned-workout row.
        session_type: SessionType code.
        paces: The plan's PaceSet, or None.

    Returns:
        A pace label; for a long run with an MP finish, ``"EF → MPR"``.
    """
    base = _session_pace_label(session_type, paces)
    if session_type == "SL" and paces is not None and _mp_finish_block(session):
        mpr = paces.pace_for("MPR")
        if mpr:
            return f"{base} → {mpr.label}"
    return base


def _parse_paces(plan: dict[str, Any]) -> Optional[PaceSet]:
    """Reconstruct the PaceSet stored in a plan's generation_params.

    Args:
        plan: Training plan row (``generation_params`` may be a dict or JSON str).

    Returns:
        The reconstructed PaceSet, or None when no paces were stored.
    """
    params = plan.get("generation_params")
    if isinstance(params, str):
        params = json.loads(params)
    if not params:
        return None
    paces = params.get("paces")
    if not paces:
        return None
    return PaceSet(**paces)


def render_plan_markdown(
    plan: dict[str, Any],
    race: dict[str, Any],
    paces: Optional[PaceSet],
    weeks: list[dict[str, Any]],
    sessions_by_week: dict[int, list[dict[str, Any]]],
) -> str:
    """Render a week-by-week markdown report of a generated plan (pure function).

    Args:
        plan: Training plan summary (name, total_weeks, start/end date, status).
        race: Race target dict.
        paces: PaceSet used for the plan, or None.
        weeks: Plan weeks ordered by week_number.
        sessions_by_week: Mapping of week id -> ordered list of session dicts.

    Returns:
        The full markdown document as a string.
    """
    lines: list[str] = []
    lines.append(f"# {plan.get('name', 'Training plan')}")
    lines.append("")
    lines.append(
        "> Plan généré par le moteur HillsRun — discipline route. "
        "Ne pas éditer à la main : régénérer via `scripts/seed_marathon_plan.py`."
    )
    lines.append("")

    # --- Overview ---------------------------------------------------------
    lines.append("## Objectif")
    lines.append("")
    lines.append(f"- **Course** : {race.get('race_name')}")
    lines.append(f"- **Date** : {race.get('race_date')}")
    lines.append(f"- **Distance** : {float(race.get('distance_km', 0)):.3f} km")
    lines.append(f"- **Objectif** : {race.get('objective')}")
    target_time = race.get("target_time_seconds")
    if target_time:
        h, rem = divmod(int(target_time), 3600)
        m, s = divmod(rem, 60)
        lines.append(f"- **Temps cible** : {h}h{m:02d}:{s:02d} ({target_time} s)")
    lines.append(
        f"- **Durée du plan** : {plan.get('total_weeks')} semaines "
        f"({plan.get('start_date')} → {plan.get('end_date')})"
    )
    lines.append("")

    # --- Paces ------------------------------------------------------------
    if paces is not None:
        lines.append("## Allures (dérivées de la VMA)")
        lines.append("")
        lines.append(f"- **VMA** : {paces.vma_kmh:.1f} km/h")
        lines.append(f"- **Source** : {paces.pace_source}")
        lines.append(
            f"- **Allure marathon projetée** : {paces.pct_marathon * 100:.0f}% VMA"
        )
        if paces.pace_objective_optimistic:
            lines.append(
                "- **Objectif optimiste** : l'allure cible est plus rapide "
                "que l'allure marathon prédite par la VMA."
            )
        lines.append("")
        lines.append("| Zone | Allure |")
        lines.append("|---|---|")
        order = ["REC", "EF", "MPR", "TMP", "INT"]
        labels = {
            "REC": "Récupération (Z1-Z2)",
            "EF": "Endurance fondamentale (Z2)",
            "MPR": "Allure marathon (Z3)",
            "TMP": "Seuil / tempo (Z3-Z4)",
            "INT": "VO2max / intervalles (Z5)",
        }
        for code in order:
            zone = paces.pace_for(code)
            if zone:
                lines.append(f"| {labels[code]} | {zone.label} |")
        lines.append("")

    # --- Weeks ------------------------------------------------------------
    lines.append("## Plan semaine par semaine")
    lines.append("")
    for week in weeks:
        phase = week.get("phase", "")
        recovery = " — récup" if week.get("is_recovery_week") else ""
        lines.append(f"### Semaine {week.get('week_number')} · {phase}{recovery}")
        lines.append("")
        lines.append(
            f"Volume cible {week.get('target_volume_km', '—')} km · "
            f"TSS {week.get('target_tss', '—')} · "
            f"{week.get('target_sessions', '—')} séances"
        )
        note = week.get("notes")
        if note:
            lines.append("")
            lines.append(f"_{note}_")
        lines.append("")
        lines.append("| Jour | Type | Séance | Durée | Distance | Allure | FC | TSS |")
        lines.append("|---|---|---|---|---|---|---|---|")
        sessions = sessions_by_week.get(week.get("id"), [])
        for s in sessions:
            stype = str(s.get("session_type", ""))
            day = _DAY_NAMES.get(s.get("day_of_week"), str(s.get("day_of_week")))
            pace = _session_pace_cell(s, stype, paces)
            hr = s.get("hr_zone_primary") or "—"
            tss = s.get("target_tss")
            tss_str = f"{tss:g}" if tss is not None else "—"
            title = s.get("title", "")
            mp_block = _mp_finish_block(s)
            if mp_block:
                title = f"{title} · {mp_block.get('description', '')}"
            lines.append(
                f"| {day} | {stype} | {title} | "
                f"{_fmt_duration(s.get('target_duration_seconds'))} | "
                f"{_fmt_distance(s.get('target_distance_meters'))} | "
                f"{pace} | {hr} | {tss_str} |"
            )
        lines.append("")

    return "\n".join(lines)


async def seed_and_generate(pool, user_id: int, out_path: Path) -> Path:
    """Seed the profile/race, generate the plan and export the markdown report.

    Args:
        pool: asyncpg connection pool.
        user_id: Garmin user ID to seed and generate for.
        out_path: Destination markdown path.

    Returns:
        The path written.
    """
    # 1. Profile
    await db_ops.upsert_athlete_profile(pool, user_id, PROFILE_DATA)
    # 2. VMA
    await set_manual_vma(pool, user_id, TARGET_VMA)
    # 3. Race target (idempotent)
    race = await find_or_create_race(pool, user_id)
    race_target_id = race["id"]
    # 4. Clear any prior plan for this race (idempotent)
    await delete_existing_plans(pool, user_id, race_target_id)

    # 5. Generate the plan
    request = GeneratePlanRequest(
        race_target_id=race_target_id,
        plan_name=f"{RACE_NAME} — Plan route",
    )
    summary = await generate_plan(pool, user_id, request)
    plan_id = summary["plan_id"]

    # 6. Read everything back for the report
    plan = await db_ops.get_training_plan(pool, plan_id, user_id)
    paces = _parse_paces(plan) if plan else None
    weeks = await db_ops.get_plan_weeks(pool, plan_id)
    sessions_by_week: dict[int, list[dict[str, Any]]] = {}
    for week in weeks:
        sessions_by_week[week["id"]] = await db_ops.get_plan_sessions_for_week(
            pool, week["id"]
        )

    markdown = render_plan_markdown(summary, race, paces, weeks, sessions_by_week)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    return out_path


async def main() -> None:
    """CLI entry point: connect, seed, generate, export, disconnect."""
    parser = argparse.ArgumentParser(
        description="Seed the road-marathon profile and generate the plan."
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        help="garmin_user.user_id to seed (default: SEED_GARMIN_USER_ID or sole user)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output markdown path (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args()

    # Load POSTGRES_* / GARMIN_* from the project .env when present, so the
    # script runs standalone without an explicit `set -a; . ./.env`.
    _load_env_file()

    db = Database(_db_config_from_env())
    await db.connect()
    try:
        user_id = await resolve_user_id(db.pool, args.user_id)
        out = await seed_and_generate(db.pool, user_id, args.out)
        print(f"Plan generated for user_id={user_id} -> {out}")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
