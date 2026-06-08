# Spec 02 — Road Marathon Adaptation of the Training Engine

> **For an autonomous coding session.** Every decision is pinned. Do not ask
> questions — implement lot by lot, run `uv run pytest` + `uv run ruff check src/`
> after each lot, and keep trail behaviour 100% backward-compatible.

## 1. Goal

The `src/training/` engine is trail-only (D+, technique, ultra, hill/descent
sessions). Add first-class support for a **road marathon** discipline so it can
generate a realistic 42.195 km road plan driven by the athlete's VMA.

Reference terrain map (exact file:line touch-points) is in the project chat;
this spec restates the decisions and acceptance criteria. Read each target file
before editing — line numbers may have drifted.

## 2. Locked athlete profile (used for the acceptance test)

| Field | Value |
|---|---|
| Experience | `intermediate` |
| Discipline | `road` |
| Race | Marathon de Brugge, **2026-10-12**, 42.195 km, **flat** (D+ ≈ 0, technical 0%) |
| Objective | `performance`, target time **3h30** (≈ 4:58/km) |
| VMA | **14.5 km/h** |
| FC max / FC repos | **188 / 56** bpm |
| Days/week | 4 runs + 1 strength |
| `day_preferences` | `{ "long_run": 7, "quality": [4], "strength": 3 }` (Tue/Sat fill as easy, Mon/Fri rest) |
| Gym access | **none** (RMU must stay bodyweight — already the case) |

Sanity check baked into the plan: marathon pace 4:58/km ÷ VMA 14.5 ⇒ **83% VMA**,
squarely in the marathon range → objective is realistic, no warning expected.

## 3. Global decisions (pinned — do not deviate)

- **New `RaceCategory.road_marathon`** (keep trail categories untouched).
- **New `RaceFlags.is_road_marathon: bool`** (default `False`).
- **New `discipline` field** on `RaceTargetInput` and DB `race_targets`
  (`VARCHAR(20)`, default `'trail'`, values `'trail' | 'road'`).
- **Marathon pace is derived from VMA**, never hardcoded. New module
  `src/training/pace_calculator.py`.
- **Only ONE new session type: `MPR`** (Marathon Pace Run). Threshold work reuses
  the existing `TMP` (already "Tempo / seuil"); VO2max work reuses `INT`.
- **`COT` / `DESC` are excluded from selection when `is_road_marathon`** (kept in
  the enum + catalog for trail).
- **`sport_type = "road_running"`** for road sessions (replace the hardcoded
  `"trail_running"` default at the point of session creation, not by changing the
  enum default — trail stays the default).
- **Long run absolute cap = 35 km for road** (vs 80 km trail); specific-phase peak
  target ≈ 30–32 km.
- **Road quality cadence:** intermediate keeps **1 quality/week** (his `quality`
  pref is a single day). Advanced/expert road plans may use 2 — implement the
  general path but the acceptance profile uses 1.
- **Objective is now honoured** (fixes known gap): `performance` → upper % VMA and
  full volume; `finish` → conservative; `midpack` → middle. See pace table.

## 4. Pace model (`pace_calculator.py`)

```
compute_paces(vma_kmh, objective) -> PaceSet
  pct_marathon = { finish: 0.78, midpack: 0.80, performance: 0.83 }[objective]
  paces (as % of VMA):
    EF  (Z2 easy)          0.70 * VMA
    MPR (Z3 marathon)      pct_marathon * VMA
    TMP (Z3-Z4 threshold)  0.88 * VMA
    INT (Z5 VO2max reps)   1.00 * VMA
  pace_min_per_km = 60 / (kmh)
  target_time_s   = (60 / (pct_marathon*VMA)) * 42.195 * 60
```

If `race_targets.target_time_seconds` is set, compute the required marathon pace
from it; if required pace is **faster** than the VMA-predicted marathon pace by
more than ~2%, attach a non-blocking warning to the plan's `generation_params`
(`pace_objective_optimistic: true`). For the acceptance profile they match.

**Expected concrete paces at VMA 14.5, objective `performance`:**

| Zone | %VMA | km/h | pace |
|---|---|---|---|
| EF | 70% | 10.15 | 5:55/km |
| MPR (marathon) | 83% | 12.04 | 4:59/km |
| TMP (threshold) | 88% | 12.76 | 4:42/km |
| INT (VO2max) | 100% | 14.5 | 4:08/km |

Target time ≈ 3h30 ✓

## 5. HR zones (Karvonen, validation only)

HRmax 188, HRrest 56, HRR 132:

| Zone | bpm |
|---|---|
| Z1 50-60% | 122–135 |
| Z2 60-70% | 135–148 |
| Z3 70-80% | 148–162 |
| Z4 80-90% | 162–175 |
| Z5 90-100% | 175–188 |

Also wire `calculate_hr_zones()` output into the generated sessions (fixes the
known gap "zones computed but never injected") — at minimum set each session's
`hr_zone` from `get_zone_for_session_type()` and store the bpm range. Keep it
small; do not refactor the catalog.

## 6. New session: `MPR` (Marathon Pace Run)

- Code `MPR`, label "Allure marathon spécifique", intensity Moderate-Hard, zone **Z3**.
- Intensity factor for TSS: **62** (between SL 55 and TMP 70).
- Templates for the 4 experience levels × phases where it applies
  (development + specific only; not base, not taper-heavy). Block structure:
  warm-up Z2 → main block at MPR pace (progressive duration by phase) → cool-down Z2.
- Appears in road catalog selection in **specific** phase primarily; may appear
  late development. Excluded for trail.

## 7. Lots (implement in order, test after each)

### Lot 1 — Discipline & classification
- `models.py`: add `road_marathon` to `RaceCategory`; add `is_road_marathon` to
  `RaceFlags`; add `discipline: str = "trail"` to `RaceTargetInput`; add `MPR` to
  `SessionType`.
- `race_classifier.py`: set `is_road_marathon=True` when `discipline=='road'` (or
  `40 <= distance <= 43` with `elevation_gain_m < 500` and `technical_percent==0`);
  set `category=road_marathon`. Pass `discipline` through.
- **Test:** classifying Brugge (42.195, D+ 0, road) → `road_marathon`,
  `is_road_marathon=True`, `is_ultra=False`.

### Lot 2 — Pace calculator
- New `src/training/pace_calculator.py` per §4 with `PaceSet` Pydantic model.
- **Test:** VMA 14.5 + `performance` → MPR 4:59/km (±2s), target_time ≈ 3h30 (±1min).

### Lot 3 — Long run (road)
- `long_run.py`: add `discipline` (+ optional `marathon_pace`) params; absolute cap
  35 km for road; replace `_get_trail_pace` with PaceSet EF pace for road; in
  specific phase, append a marathon-pace finish block flag.
- **Test:** 16-week intermediate road plan long-run peak between 28 and 35 km,
  never > 35; taper long run reduced.

### Lot 4 — Catalog, load, zones
- `session_catalog.py`: add `MPR` templates; in `get_phase_session_types`, for
  `is_road_marathon` exclude `COT`/`DESC`, include `MPR` (specific) + `TMP`/`INT`;
  road duration ranges use road paces.
- `load_calculator.py`: add `MPR: 62`; keep COT/DESC factors (unused for road).
- `hr_zones.py`: map `MPR → Z3`.
- **Test:** road specific-phase week contains no COT/DESC; contains MPR or TMP/INT.

### Lot 5 — Week builder & generator wiring
- `week_builder.py`: `_get_quality_type_order` for road → `[TMP, INT, MPR]`
  (skip COT); no D+ target on road long run; honour `day_preferences`
  (long_run=7, quality=[4], strength=3, easy fill Tue/Sat).
- `plan_generator.py`: compute `PaceSet` from `fitness.vma_kmh` + objective; pass
  discipline/paces to long_run + week builder; set `sport_type="road_running"` for
  road sessions; store paces + any warning in `generation_params`; inject hr_zone.
- **Test:** end-to-end (see §8).

### Lot 6 — DB & API
- New migration `sql/11_road_marathon.sql`:
  ```sql
  ALTER TABLE race_targets ADD COLUMN IF NOT EXISTS discipline VARCHAR(20) NOT NULL DEFAULT 'trail';
  ALTER TABLE race_targets ADD COLUMN IF NOT EXISTS target_time_seconds INTEGER;
  ```
  (sport_type default in `training_plan_sessions` stays `'trail_running'`; set
  `'road_running'` explicitly at insert for road plans.)
- `src/api/routers/training_plans.py`: add optional `discipline` (default `"road"`
  acceptable) and `target_time_seconds` to `RaceTargetCreate`; thread into
  `create_race_target`. No change to the `/generate` endpoint signature.

## 8. End-to-end acceptance test

Create a pytest fixture with the §2 profile and assert a generated 16-week plan:
- `race_category == road_marathon`, sessions `sport_type == "road_running"`.
- 4 phases present; taper ≥ 2 weeks; recovery weeks every 3 (intermediate).
- 4 running sessions/week + RMU on Wednesday(3); long run Sunday(7); quality
  Thursday(4); easy Tue(2)/Sat(6).
- No `COT`/`DESC` sessions anywhere.
- Long-run peak 28–35 km.
- Weekly TSS progression never exceeds +15% (existing rule still passes).
- MPR pace ≈ 4:59/km, EF ≈ 5:55/km in the stored session paces.

## 9. Guardrails

- `uv` only (never pip). Google-style docstrings on new functions. Comments/UI in
  English, per repo conventions.
- Run `uv run pytest tests/` and `uv run ruff check src/ && uv run ruff format src/`
  after every lot; do not finish red.
- **Do not** alter trail behaviour: existing trail tests must stay green. New code
  paths are gated on `discipline == 'road'` / `is_road_marathon`.
- Keep diffs surgical — no opportunistic refactors of the catalog or DB layer.

## 10. Done = PR

Branch `feat/road-marathon-engine`. Commit per lot with clear messages. Open a PR
summarising the new discipline, the pace model, and the acceptance test, listing
which known gaps were closed (objective honoured, HR zones injected).
