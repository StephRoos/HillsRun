## Road-marathon engine + adaptive coach

Adds a **road-marathon training engine** (Sprint A, spec 02) and a
**non-destructive adaptive coach** (Sprint D, spec 03) on top of the existing
trail plan generator. Trail behaviour is unchanged throughout — every road/
adaptive path is gated on `discipline == "road"` / `is_road_marathon` or is a
purely additive read-only/propose-only layer.

### Sprint A — Road marathon (spec 02)
- **Discipline & classification**: `RaceCategory.road_marathon`,
  `RaceFlags.is_road_marathon`, `RaceTargetInput.discipline` (default `trail`),
  `SessionType.MPR`. `classify_race` short-circuits road → marathon flags.
- **Pace model** (`pace_calculator.py`): VMA-derived paces (REC/EF ranges,
  MPR/TMP/INT single), target-time projection, optimistic-goal flag. **VDOT
  fallback** from VO2max when VMA is absent.
- **Long-run variants**: absolute 35 km road cap, progressive / marathon-pace-
  block / fast-finish by phase, taper keeps intensity (Wang 2023).
- **Catalogue / load / zones**: full MPR templates (dev+specific), COT/DESC
  excluded for road, MPR load factor 62, MPR → Z3, road taper keeps a touch of
  intensity.
- **Wiring**: `week_builder` road quality order `[TMP,INT,MPR]` (no D+ on road
  LR); `plan_generator` computes a `PaceSet`, dual-writes `road_running`,
  injects HR zones, stores paces + warning in `generation_params`.
- **DB/API**: `sql/11_road_marathon.sql` (discipline + target_time_seconds);
  `RaceTargetCreate` accepts the new fields. Acceptance suite asserts peak LR
  28–35 km, no COT/DESC in road specific weeks, derived paces.
- **Seed**: `scripts/seed_marathon_plan.py` upserts the Brugge 2026-10-12
  marathon (VMA 14.5, target 3h30) and exports `specs/mon-plan-marathon.md`.

### Sprint D — Adaptive coach (spec 03)
Evidence stance is explicit and unchanged from the research synthesis:
- **Core signal = morning HRV vs individual baseline** (the only validated
  method): `readiness.py` builds the ln(rMSSD) band over 60 days (≥28 points),
  with 2-day RED hysteresis and secondary signals that may only nudge a
  borderline GREEN.
- **ACWR is informational/contested** — surfaced under `acwr_informational`
  with a contested note, **never** a decision gate.
- **Garmin Training Readiness is secondary** — a margin modifier only.
- **D1** daily verdict (`/api/v1/training/daily-readiness`) — non-destructive.
- **D2** Claude reasoning layer (Haiku 4.5), anchored on D1: explains/refines
  tone but can never relax a RED.
- **D3** read-only planned-vs-actual reconciliation
  (`/api/v1/training-plans/{id}/reconcile`): compliance, realized TSS.
- **D4** **PROPOSE-ONLY** weekly adjuster (`plan_adjuster.py`): keep next week
  stable after missed sessions, insert a recovery week on sustained AMBER/RED +
  low compliance, or progress +15% TSS (labelled heuristic) when consistently
  green and ahead; pace recompute on a meaningful VMA shift. Anti-thrashing:
  ≤1 structural change per week.
  - **No plan mutation happens without explicit user apply.** Generating a
    proposal writes only to `weekly_reconciliations`; the plan rows are touched
    only by `POST /{plan_id}/adjustments/{proposal_id}/apply`.

### Migrations (apply manually to Neon + NAS after merge — none auto-applied)
`sql/11_road_marathon.sql`, `sql/12_daily_recommendations.sql`,
`sql/13_ai_rationale.sql`, `sql/14_weekly_reconciliations.sql`.

### Tests
Full suite **940 passed** / 2 pre-existing env-dependent failures (CORS
env-override, MFA cleanup) — unchanged baseline. New coverage: pace calculator,
long-run variants, road acceptance, seed export, D1–D4 (readiness, agent,
reconcile, plan adjuster).
