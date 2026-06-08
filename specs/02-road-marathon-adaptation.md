# Spec 02 — Road Marathon Adaptation of the Training Engine

> **For an autonomous coding session.** Every decision is pinned. Do not ask
> questions — implement lot by lot, run `uv run pytest` + `uv run ruff check src/`
> after each lot, and keep trail behaviour 100% backward-compatible.
>
> _Revised after audit (2026-06-08): MPR enum+templates land together, VDOT
> fallback, easy/recovery pace + HR binding, marathon long-run variants,
> pure-function acceptance tests, plus a "last mile" seed task (§11)._

## 1. Goal

The `src/training/` engine is trail-only (D+, technique, ultra, hill/descent
sessions). Add first-class support for a **road marathon** discipline so it can
generate a realistic 42.195 km road plan driven by the athlete's VMA.

Read each target file before editing — line numbers may have drifted.

## 2. Locked athlete profile (used for the acceptance test + §11 seed)

| Field | Value |
|---|---|
| Experience | `intermediate` |
| Discipline | `road` |
| Race | Marathon de Brugge, **2026-10-12**, 42.195 km, **flat** (D+ ≈ 0, technical 0%) |
| Objective | `performance`, target time **3h30** (12600 s, ≈ 4:58/km) |
| VMA | **14.5 km/h** |
| FC max / FC repos | **188 / 56** bpm |
| Days/week | 4 runs + 1 strength |
| `day_preferences` | `{ "long_run": 7, "quality": [4], "strength": 3 }` (Tue/Sat fill as easy, Mon/Fri rest) |
| Gym access | **none** (RMU stays bodyweight — already the case) |

Sanity check: marathon pace 4:58/km ÷ VMA 14.5 ⇒ **83% VMA**, in the marathon
range → objective realistic, no warning expected.

## 3. Global decisions (pinned — do not deviate)

- **New `RaceCategory.road_marathon`** (keep trail categories untouched).
- **New `RaceFlags.is_road_marathon: bool`** (default `False`).
- **New `discipline` field** on `RaceTargetInput` and DB `race_targets`
  (`VARCHAR(20)`, default `'trail'`, values `'trail' | 'road'`).
- **`SessionType.MPR` (Marathon Pace Run) is added together with at least minimal
  catalog templates** — `get_session_template` raises `ValueError` on a missing
  key (`session_catalog.py:51`), so never ship the enum without templates.
- Threshold work reuses existing `TMP` ("Tempo / seuil"); VO2max work reuses `INT`.
- **`COT` / `DESC` excluded from selection when `is_road_marathon`** (kept for
  trail; the trail no-flags path must still include `COT`, cf
  `tests/test_training/test_session_catalog.py:65`).
- **Marathon pace derived from VMA**, never hardcoded. New module
  `src/training/pace_calculator.py`. **VDOT fallback** from VO2max when VMA is
  absent (`_get_vma` returns `None`).
- **`sport_type = "road_running"`** for road sessions (set at session creation for
  both dual-write rows; do not change the enum default — trail stays default).
- **Long run absolute cap = 35 km for road**; specific-phase peak ≈ 30–32 km.
- **Easy/recovery runs are HR-bound (Z2)**, pace is a range, not a single value —
  prevents the classic "easy runs too fast" marathon error.
- **Objective is honoured** (fixes known gap): `performance` → upper % VMA + full
  volume; `finish` → conservative; `midpack` → middle.

## 4. Pace model (`pace_calculator.py`)

```
compute_paces(vma_kmh, objective) -> PaceSet
  pct_marathon = { finish: 0.78, midpack: 0.80, performance: 0.83 }[objective]
  paces as % of VMA (RANGES for easy efforts):
    REC (Z1-Z2 recovery)   0.63 – 0.67 * VMA   (HR-bound Z1/low-Z2)
    EF  (Z2 easy)          0.68 – 0.72 * VMA   (HR-bound Z2 — pace secondary)
    MPR (Z3 marathon)      pct_marathon * VMA
    TMP (Z3-Z4 threshold)  0.88 * VMA
    INT (Z5 VO2max reps)   1.00 * VMA
  pace_min_per_km = 60 / kmh ; target_time_s = (60/(pct_marathon*VMA)) * 42.195 * 60
```

**VDOT fallback** (VMA absent): estimate VMA from running VO2max
(`vma_kmh ≈ vo2max / 3.5`) then apply the same percentages; attach
`pace_source: "vo2max_estimate"` to the plan's `generation_params`.

If `race_targets.target_time_seconds` is set, compute required marathon pace from
it; if required pace is faster than the VMA-predicted marathon pace by > ~2%,
attach `pace_objective_optimistic: true` (non-blocking). For the §2 profile they
match.

**Expected concrete paces at VMA 14.5, objective `performance`:**

| Zone | %VMA | km/h | pace |
|---|---|---|---|
| REC | 65% | 9.43 | 6:22/km |
| EF | 70% | 10.15 | 5:55/km |
| MPR (marathon) | 83% | 12.04 | 4:59/km |
| TMP (threshold) | 88% | 12.76 | 4:42/km |
| INT (VO2max) | 100% | 14.5 | 4:08/km |

Target time ≈ 3h30 ✓

## 5. HR zones (Karvonen) + injection

HRmax 188, HRrest 56, HRR 132:

| Zone | bpm |
|---|---|
| Z1 50-60% | 122–135 |
| Z2 60-70% | 135–148 |
| Z3 70-80% | 148–162 |
| Z4 80-90% | 162–175 |
| Z5 90-100% | 175–188 |

Wire `calculate_hr_zones()` into generated sessions (fixes "zones computed but
never injected"): set each session's `hr_zone` from `get_zone_for_session_type()`
and store the bpm range. Keep it small; no catalog refactor.

## 6. New session `MPR` + marathon long-run variants

**`MPR` (Marathon Pace Run):** code `MPR`, label "Allure marathon spécifique",
zone **Z3**, TSS intensity factor **62** (between SL 55 and TMP 70). Templates for
4 levels, in **development + specific** phases (not base/taper). Block: warm-up
Z2 → main block at MPR pace (duration grows by phase) → cool-down Z2. Excluded for
trail.

**Long-run variants by phase (road):**
- **Base / development:** progressive easy long run (EF, HR Z2).
- **Specific:** long run with a **marathon-pace finish block** (e.g. 30 km with the
  last 10–12 km at MPR) and occasional **fast-finish**.
- **Taper:** shortened, mostly EF with a few minutes at MPR to stay sharp.

## 7. Lots (implement in order, test after each)

### Lot 1 — Discipline, classification + MPR stub
`models.py`: add `road_marathon`, `is_road_marathon`, `discipline`, `SessionType.MPR`.
`race_classifier.py`: set `is_road_marathon`/`road_marathon` for road. **Add minimal
MPR templates** in `_build_catalog` so no `ValueError`. **Test:** Brugge → road_marathon,
`is_road_marathon=True`, `is_ultra=False`; full suite stays green.

### Lot 2 — Pace calculator (+ VDOT fallback)
New `pace_calculator.py` per §4 with a `PaceSet` model, ranges for REC/EF, VDOT
fallback. **Test:** VMA 14.5 + `performance` → MPR 4:59/km (±2s), target ≈ 3h30;
VO2max fallback path covered.

### Lot 3 — Long run (road) + variants
`long_run.py`: `discipline` (+ optional `marathon_pace`) params; 35 km cap for road;
EF pace from PaceSet; HR Z2 binding; phase variants per §6. **Test:** peak 28–35 km,
never > 35; MP finish block present in specific phase; taper reduced.

### Lot 4 — Catalog (full MPR), load, zones
`session_catalog.py`: complete MPR templates; in `get_phase_session_types`, gate
`is_road_marathon` to drop COT/DESC + add MPR; road duration ranges. `load_calculator.py`:
`MPR: 62`. `hr_zones.py`: `MPR → Z3`. **Test:** no COT/DESC in road specific week;
trail no-flags still has COT.

### Lot 5 — Week builder & generator wiring
`week_builder.py`: road quality order `[TMP, INT, MPR]` (skip COT); no D+ on road long
run; honour `day_preferences`. `plan_generator.py`: compute `PaceSet` (VMA+objective,
VDOT fallback); pass discipline/paces to long_run + week builder; `sport_type="road_running"`
on both dual-write rows; inject hr_zone; store paces + warnings in `generation_params`.

### Lot 6 — DB, API, tests, PR
Migration `sql/11_road_marathon.sql`:
```sql
ALTER TABLE race_targets ADD COLUMN IF NOT EXISTS discipline VARCHAR(20) NOT NULL DEFAULT 'trail';
ALTER TABLE race_targets ADD COLUMN IF NOT EXISTS target_time_seconds INTEGER;
```
`RaceTargetCreate`: optional `discipline` + `target_time_seconds`. **Do NOT apply the
migration to prod** (manual step, §12). **Tests:** prefer **pure-function assertions**
(`pace_calculator`, `long_run`, `week_builder`) for peak 28–35, no COT/DESC, paces;
plus a light e2e smoke via the **existing mock-pool pattern** (`AsyncMock`, see
`tests/test_training/test_plan_generator.py`). Open the PR (§10).

### Lot 7 — Last mile: seed + generate MY plan (§11)
See §11.

## 8. Acceptance assertions (pure-function first)

Assert mostly on pure functions (no DB):
- `classify_race` Brugge → `road_marathon`, `is_road_marathon`.
- `pace_calculator` VMA 14.5 perf → MPR 4:59, EF range ~5:50–6:00, REC ~6:20.
- `long_run` 16-week intermediate road: peak 28–35 km, MP block in specific phase.
- `get_phase_session_types(is_road_marathon=True)` specific phase: no COT/DESC,
  contains MPR / TMP / INT.
- `week_builder` honours day_preferences (long_run Sun(7), quality Thu(4), strength
  Wed(3), easy Tue(2)/Sat(6)); no two hard days in a row.

Plus one mocked-pool smoke of `generate_plan` asserting `sport_type=="road_running"`
and 4 phases with taper ≥ 2 weeks, weekly TSS progression ≤ +15%.

## 9. Guardrails

- `uv` only. Google-style docstrings on new functions. Code/UI in English.
- `uv run pytest tests/` + `uv run ruff check src/ && uv run ruff format src/` after
  every lot; never finish red; trail tests must stay green.
- New code paths gated on `discipline == 'road'` / `is_road_marathon`.
- Surgical diffs — no opportunistic refactors of catalog or DB layer.

## 10. Done = PR

Branch `feat/road-marathon-engine`. One commit per lot. PR summarises the new
discipline, pace model, long-run variants, and which known gaps were closed
(objective honoured, HR zones injected).

## 11. Last mile — seed and generate MY plan (Lot 7)

The engine being green does not give Stephane a plan: no data is seeded. Create
`scripts/seed_marathon_plan.py` (run with `uv run`) that is **idempotent** and:
1. upserts `athlete_profile` (intermediate, fc_max 188, fc_repos 56,
   `day_preferences = {long_run:7, quality:[4], strength:3}`, gym_access false);
2. sets `garmin_user.manual_vma = 14.5`;
3. creates the `race_target` (Marathon de Brugge, 2026-10-12, discipline `road`,
   42.195 km, D+ 0, objective `performance`, `target_time_seconds = 12600`);
4. calls `generate_plan` and **exports** the plan to `specs/mon-plan-marathon.md`
   (week by week: phase, sessions with day, type, duration, pace, HR zone, TSS).

No secrets committed (read DB creds from env). A smoke test asserts the script runs
and produces the markdown. Stephane reviews `specs/mon-plan-marathon.md` on waking.

## 12. Out of scope tonight — manual / follow-up

- **Apply `sql/11` manually** to Neon (primary) **and** the NAS replica after merge
  — migrations are applied by hand in this project; the agent must NOT touch prod.
- **Frontend follow-up (separate mini-PR):** add a `discipline` selector to the
  wizard (`web/.../training-plan/new/page.tsx`) and hide D+/technical fields in road
  mode, so the plan can be generated self-service from the UI.
- **Summer heat / hydration** for the June→October block ties into the nutrition
  chantiers (B/C), not this engine work.
