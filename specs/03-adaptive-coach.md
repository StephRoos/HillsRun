# Spec 03 — Adaptive Coach (Chantier D)

> **For the same autonomous run as spec 02, AFTER its lots.** Evidence-based
> thresholds come from the verified research synthesis
> (`SecondBrain/03-Resources/dev-notes/recherche-marathon-ajustement-dynamique.md`).
> Python/uv. `uv run pytest` + `uv run ruff` after each lot. Non-destructive by
> default; the only plan-mutating lot (D4) is **propose-only**.

## 0. Why & guardrails (read first)

Make the static plan **react to reality** using Garmin data already in the DB.
Evidence stance (do not deviate):
- **Core signal = morning HRV vs individual baseline.** This is the validated method.
- **ACWR is CONTESTED** (no confirmed safe-range; anti-ACWR also refuted) → may be
  shown as **informational only**, never a hard gate.
- **Garmin Training Readiness is NOT independently validated** → secondary/convenience
  signal only.
- HRV-guided training does **not** beat a fixed plan on peak performance; it gives
  equal results with fewer hard sessions + less overreach. **Frame D as timing &
  overreach management, never a "performance booster."**
- **Anti-thrashing is structural:** react to a baseline **range/band** (hysteresis),
  do daily decisions for *today's session only*, batch *structural* plan changes weekly.

## 1. Core rule — daily GO / EASE / REST (HRV-baseline)

```
baseline (per athlete, rebuilt weekly from stored daily HRV, >= 4 weeks of data):
  x = ln(rMSSD) daily values over trailing 60 days (>= 28 required)
  mean_ln, sd_ln = mean/sd of x
  normal_range = [mean_ln - 0.5*sd_ln, mean_ln + 0.5*sd_ln]

today (morning value ln(rMSSD_today)):
  >= lower bound  -> GREEN  (proceed with planned session)
  < lower bound   -> AMBER  (downgrade quality -> easy, or cut duration ~20-30%)
  << lower (e.g. < mean_ln - 1.0*sd_ln) for 2+ consecutive days -> RED (rest / active recovery)
```
- If `< 28` daily HRV points exist, output `verdict = "insufficient_baseline"` and fall
  back to the planned session (no adjustment). Stephane has ~90 days Garmin history,
  so the baseline bootstraps immediately.
- **Secondary modifiers** (only nudge AMBER↔GREEN at the margin, never override a RED,
  flagged non-validated): sleep_score < 50, resting HR > baseline + 5 bpm, Garmin
  training_readiness < 30. Never let secondary signals alone trigger a downgrade.

## 2. Data sources (already in DB — inspect schema before coding)

| Signal | Table | Use |
|---|---|---|
| Daily HRV (rMSSD / overnight) | `hrv` | baseline + today's value (CORE) |
| Sleep score | `sleep` | secondary modifier |
| Resting HR | `daily_summary` | secondary modifier (vs baseline) |
| Garmin training readiness | `training_readiness` | secondary, informational |
| Planned session of the day | `planned_workouts` | what we may downgrade |
| Completed activities | `activities` | D3 reconciliation |

## 3. Lots (run after spec 02's lots; one commit each)

### Lot D1 — HRV baseline + daily verdict (rule-based, non-destructive)
- New package `src/training/adaptive/` + `readiness.py`: `build_hrv_baseline(values)`,
  `daily_verdict(today, baseline, secondary)` per §1 (pure functions, fully unit-tested).
- New table (migration `sql/12_daily_recommendations.sql`): `daily_recommendations`
  (id, user_id, date, verdict, reason, suggested_modification jsonb, hrv_value,
  baseline_low, baseline_high, accepted bool default false, created_at).
- Endpoint `GET /api/v1/training/daily-readiness?date=` returning verdict + reason +
  suggested modification (does NOT mutate the plan).
- **Test:** band logic (green/amber/red), insufficient-baseline fallback, hysteresis
  (single dip inside band → still GREEN).

### Lot D2 — AI reasoning layer (non-destructive)
- `readiness_agent.py`: given the signals + today's planned session + last 3 days
  context, produce a **structured** recommendation (verdict, modification, short
  natural-language rationale) via the **Claude API** (anthropic SDK, server-side key;
  default model Haiku 4.5 for cost, Sonnet 4.6 if quality needed). The rule-based
  verdict from D1 is the **anchor**; the agent explains and refines tone, never
  contradicts a RED.
- Persist the rationale alongside the D1 verdict. Add an `X-API-Key`-protected
  endpoint or extend `/daily-readiness?explain=true`.
- **Test:** mock the LLM call; assert structured output schema + that agent cannot
  upgrade a RED to GREEN.

### Lot D3 — Planned vs actual reconciliation (read-only)
- `workout_matcher.py`: match each `planned_workout` to the nearest `activity`
  (same day ±1, sport type tolerance). `adherence.py`: per-week compliance
  (completed?, actual vs planned duration/distance/pace/TSS), realized weekly TSS.
- **ACWR informational only** (if computed at all): expose under a clearly-labelled
  `acwr_informational` field with a contested note; NEVER gate decisions on it.
- Endpoint `GET /api/v1/training-plans/{id}/reconcile?week=` → read-only report.
- **Test:** matching tolerance, compliance math, realized-TSS aggregation.

### Lot D4 — Weekly adjustment (PROPOSE-ONLY)
- `plan_adjuster.py`: from D3 adherence, **propose** changes to upcoming weeks:
  - missed sessions → do NOT pile up; keep next week stable (no jump).
  - sustained AMBER/RED + low compliance → insert/extend a recovery week.
  - consistently green + ahead → allow slightly faster progression (within the +15%
    TSS heuristic — label heuristic, not evidence-based).
  - **Pace recompute:** when the weekly-updated baseline / VO2max shifts meaningfully,
    recompute target paces via `pace_calculator`. (The weekly baseline answers "when
    to recompute" — it self-recalibrates.)
- Output a **proposal object** stored in `weekly_reconciliations`; an optional
  `apply` endpoint requires explicit user action. **No auto-apply.**
- **Test:** proposals are generated but the plan rows are unchanged unless `apply`
  is called; anti-thrashing (no structural change more than once per week).

## 4. Sequencing & scope for tonight
- Order: D1 → D2 → D3 → D4. D1–D3 are non-destructive; D4 is propose-only.
- This is appended to spec 02's queue → one continuous run: **Sprint A then Sprint D**.

## 5. Done = PR
Same branch as spec 02. The Chantier-D portion of the PR description must state the
evidence basis (HRV-baseline core, ACWR informational/contested, Garmin TR secondary)
and that no plan mutation happens without explicit user apply.

## 6. Out of scope / manual
- Apply migrations `sql/12` (and any new) manually to Neon + NAS after merge.
- Wire the daily readiness verdict into the existing 05:00 sync cron (small follow-up).
- Frontend "Recommandation du jour" card — separate mini-PR (like the wizard discipline selector).
