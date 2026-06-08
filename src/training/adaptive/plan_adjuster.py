"""Weekly plan adjustment proposals (Lot D4, PROPOSE-ONLY).

From the read-only adherence report (Lot D3) plus the recent daily readiness
verdicts (Lot D1), this module *proposes* — never applies — changes to the
upcoming week of a training plan:

- missed sessions -> keep next week stable (do **not** pile the lost load on);
- sustained AMBER/RED + low compliance -> insert/extend a recovery week;
- consistently green + ahead of plan -> allow slightly faster progression
  (a labelled ``+15%`` TSS *heuristic*, explicitly not evidence-based);
- a meaningful VMA/VO2max shift -> recompute target paces via ``pace_calculator``.

Everything here is a pure function of its inputs (no DB, no I/O) so the
heuristics stay fully unit-testable. **Anti-thrashing is structural:** at most
one *structural* change (recovery insert / acceleration) is proposed per week.
Applying a proposal requires an explicit user action elsewhere — this module
never mutates a plan.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel

from .adherence import WeekAdherence
from ..models import RaceObjective
from ..pace_calculator import PaceSet, compute_paces

# Compliance bands (% of planned sessions completed).
_LOW_COMPLIANCE_PCT = 60.0
_HIGH_COMPLIANCE_PCT = 90.0

# Heuristic load multipliers (labelled non-evidence-based per spec §3).
_ACCELERATE_TSS_FACTOR = 1.15  # consistently green + ahead -> +15%
_RECOVERY_TSS_FACTOR = 0.6  # inserted/extended recovery week -> cut volume

# Sustained fatigue from the recent daily verdicts: either enough AMBER/RED days
# combined, or a smaller number of outright RED days.
_SUSTAINED_FATIGUE_DAYS = 3
_SUSTAINED_RED_DAYS = 2

# Minimum relative VMA shift before recomputing paces is worthwhile.
_PACE_RECOMPUTE_THRESHOLD = 0.03

_HEURISTIC_LABEL = "heuristic (not evidence-based)"
_EVIDENCE_LABEL = "evidence-based (HRV-baseline + compliance)"


class AdjustmentAction(str, Enum):
    """The kind of change a proposal carries (string-valued for JSON/DB)."""

    MAINTAIN = "maintain"  # keep the upcoming week as planned (no pile-up)
    INSERT_RECOVERY = "insert_recovery"  # convert/extend an upcoming recovery week
    ACCELERATE = "accelerate"  # slightly faster progression (+15% TSS heuristic)
    RECOMPUTE_PACES = "recompute_paces"  # refresh target paces after a VMA shift


class ProposedChange(BaseModel):
    """A single proposed change to an upcoming plan week (not applied)."""

    action: AdjustmentAction
    target_week: Optional[int] = None
    structural: bool = False  # counts against the one-per-week anti-thrashing cap
    tss_factor: Optional[float] = None  # multiplier to apply to the week's TSS
    rationale: str = ""
    evidence_label: str = _EVIDENCE_LABEL
    details: dict = {}


class WeeklyAdjustmentProposal(BaseModel):
    """A propose-only adjustment for the week following the evaluated one.

    ``auto_apply`` is always ``False``: applying requires an explicit user
    action via the dedicated endpoint. The plan rows are untouched until then.
    """

    plan_id: Optional[int] = None
    from_week: int  # the just-completed / evaluated week
    target_week: int  # the upcoming week the changes apply to
    compliance_pct: float = 0.0
    summary: str = ""
    changes: list[ProposedChange] = []
    recomputed_paces: Optional[dict] = None
    auto_apply: bool = False

    @property
    def structural_change_count(self) -> int:
        """How many structural changes the proposal carries (cap is 1)."""
        return sum(1 for c in self.changes if c.structural)


def _count_fatigue(recent_verdicts: list[str]) -> tuple[int, int]:
    """Return ``(amber_days, red_days)`` from a list of recent daily verdicts."""
    amber = sum(1 for v in recent_verdicts if v == "amber")
    red = sum(1 for v in recent_verdicts if v == "red")
    return amber, red


def _is_sustained_fatigue(amber: int, red: int) -> bool:
    """Whether the recent verdicts show sustained fatigue (spec §3)."""
    return red >= _SUSTAINED_RED_DAYS or (amber + red) >= _SUSTAINED_FATIGUE_DAYS


def propose_weekly_adjustment(
    week_report: WeekAdherence,
    recent_verdicts: list[str],
    *,
    from_week: int,
    target_week: Optional[int] = None,
) -> WeeklyAdjustmentProposal:
    """Propose (never apply) an adjustment for the week after ``from_week``.

    The proposal carries **at most one structural change** (recovery insert or
    acceleration) plus optional non-structural notes. A missed-session week with
    no fatigue signal yields a ``MAINTAIN`` note (keep the upcoming week stable —
    do not pile the lost load on).

    Args:
        week_report: The Lot D3 adherence report for the evaluated week.
        recent_verdicts: Recent daily readiness verdicts (e.g. last ~10 days),
            values among ``green``/``amber``/``red``/``insufficient_baseline``.
        from_week: The evaluated (just-completed) plan week number.
        target_week: The upcoming week to adjust (defaults to ``from_week + 1``).

    Returns:
        A :class:`WeeklyAdjustmentProposal` (``auto_apply`` always ``False``).
    """
    target = target_week if target_week is not None else from_week + 1
    compliance = week_report.compliance_pct
    amber, red = _count_fatigue(recent_verdicts)
    sustained = _is_sustained_fatigue(amber, red)
    ahead = (
        week_report.planned_tss > 0
        and week_report.realized_tss >= week_report.planned_tss
    )
    missed = week_report.completed_sessions < week_report.planned_sessions

    changes: list[ProposedChange] = []

    # --- The single structural decision (mutually exclusive by construction) ---
    if sustained and compliance < _LOW_COMPLIANCE_PCT:
        changes.append(
            ProposedChange(
                action=AdjustmentAction.INSERT_RECOVERY,
                target_week=target,
                structural=True,
                tss_factor=_RECOVERY_TSS_FACTOR,
                rationale=(
                    f"Sustained fatigue ({amber} AMBER / {red} RED recent days) with "
                    f"low compliance ({compliance:.0f}%) — turn week {target} into a "
                    "recovery week (cut volume, keep it easy)."
                ),
                evidence_label=_EVIDENCE_LABEL,
            )
        )
    elif compliance >= _HIGH_COMPLIANCE_PCT and ahead and not sustained:
        changes.append(
            ProposedChange(
                action=AdjustmentAction.ACCELERATE,
                target_week=target,
                structural=True,
                tss_factor=_ACCELERATE_TSS_FACTOR,
                rationale=(
                    f"Consistently green and ahead of plan (compliance {compliance:.0f}%, "
                    f"realized {week_report.realized_tss:.0f} >= planned "
                    f"{week_report.planned_tss:.0f} TSS) — progress week {target} "
                    "slightly faster (+15% TSS)."
                ),
                evidence_label=_HEURISTIC_LABEL,
            )
        )

    # --- Non-structural note: missed sessions must NOT pile up. ---
    has_structural = any(c.structural for c in changes)
    if missed and not has_structural:
        changes.append(
            ProposedChange(
                action=AdjustmentAction.MAINTAIN,
                target_week=target,
                structural=False,
                rationale=(
                    f"{week_report.planned_sessions - week_report.completed_sessions} "
                    f"missed session(s) — keep week {target} as planned; do not pile "
                    "the lost load on."
                ),
                evidence_label=_EVIDENCE_LABEL,
            )
        )

    # --- Default: on track, hold the plan. ---
    if not changes:
        changes.append(
            ProposedChange(
                action=AdjustmentAction.MAINTAIN,
                target_week=target,
                structural=False,
                rationale=(
                    f"On track (compliance {compliance:.0f}%) — keep week {target} "
                    "as planned."
                ),
                evidence_label=_EVIDENCE_LABEL,
            )
        )

    # Anti-thrashing safety net: enforce at most one structural change even if a
    # future edit adds another branch above.
    changes = _cap_structural_changes(changes)

    summary = changes[0].rationale
    return WeeklyAdjustmentProposal(
        from_week=from_week,
        target_week=target,
        compliance_pct=compliance,
        summary=summary,
        changes=changes,
        auto_apply=False,
    )


def _cap_structural_changes(
    changes: list[ProposedChange], *, max_structural: int = 1
) -> list[ProposedChange]:
    """Drop structural changes beyond ``max_structural`` (keep non-structural)."""
    kept: list[ProposedChange] = []
    structural_seen = 0
    for change in changes:
        if change.structural:
            if structural_seen >= max_structural:
                continue
            structural_seen += 1
        kept.append(change)
    return kept


def should_recompute_paces(
    current_vma_kmh: Optional[float],
    new_vma_kmh: Optional[float],
    *,
    threshold: float = _PACE_RECOMPUTE_THRESHOLD,
) -> bool:
    """Whether the VMA shifted enough to warrant a pace recompute.

    Args:
        current_vma_kmh: VMA the plan's paces were built from.
        new_vma_kmh: Latest VMA (e.g. manual or fitness-derived).
        threshold: Minimum relative change (default 3%).

    Returns:
        ``True`` when both values are positive and the relative change exceeds
        ``threshold``.
    """
    if not current_vma_kmh or not new_vma_kmh or current_vma_kmh <= 0:
        return False
    return abs(new_vma_kmh - current_vma_kmh) / current_vma_kmh > threshold


def maybe_recompute_paces(
    current_vma_kmh: Optional[float],
    new_vma_kmh: Optional[float],
    *,
    objective: RaceObjective = RaceObjective.finish,
    target_time_seconds: Optional[int] = None,
    threshold: float = _PACE_RECOMPUTE_THRESHOLD,
) -> Optional[PaceSet]:
    """Recompute the pace set when VMA has shifted meaningfully, else ``None``.

    The weekly-rebuilt baseline answers *when* to recompute: the plan's stored
    VMA is compared to the latest VMA and paces are only refreshed past the
    relative ``threshold``.

    Args:
        current_vma_kmh: VMA the current paces were derived from.
        new_vma_kmh: Latest VMA in km/h.
        objective: Race objective driving the marathon-pace fraction.
        target_time_seconds: Optional goal marathon time (optimistic flag).
        threshold: Minimum relative VMA change to trigger a recompute.

    Returns:
        A fresh :class:`PaceSet`, or ``None`` if no meaningful shift.
    """
    if not should_recompute_paces(current_vma_kmh, new_vma_kmh, threshold=threshold):
        return None
    return compute_paces(
        new_vma_kmh,
        objective=objective,
        target_time_seconds=target_time_seconds,
        pace_source="vma",
    )
