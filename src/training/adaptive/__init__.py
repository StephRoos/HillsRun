"""Adaptive coach package (Chantier D).

Makes the static training plan react to reality using Garmin data already in
the DB. The core signal is morning HRV versus an individual baseline (the only
research-validated method). ACWR is treated as informational/contested and
Garmin Training Readiness as a secondary convenience signal — never hard gates.

Non-destructive by default: nothing here mutates a generated plan. The verdict
helpers (``readiness``) are pure functions; DB access lives in ``queries``.
"""
