#!/usr/bin/env python3
"""Seed the Athora Bruges Marathon plan (Fable 5) as planned_workouts.

Faithful encoding of `specs/03-brugge-marathon-plan.md`. The plan is data-only:
each coaching session becomes a dated row for the calendar model
(`planned_workouts`), for `user_id = 70`.

Usage:
    python scripts/seed_brugge_plan.py --summary   # counts, no side effects
    python scripts/seed_brugge_plan.py --sql       # idempotent SQL to stdout (default)
    python scripts/seed_brugge_plan.py --csv       # CSV (import-endpoint shape)

The SQL is meant to be piped into the UM880 prod DB under supervision, e.g.:
    python scripts/seed_brugge_plan.py --sql \\
      | ssh homelab "docker exec -i <db_container> psql -U garmin -d garmin_connect"

It is idempotent: it clears the user's planned workouts in the plan window and
removes the auto-generated wizard plan before inserting the coach sessions.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from dataclasses import dataclass
from datetime import date, timedelta

USER_ID = 70

# Race target already exists (id 4); we realign its goal time to the plan.
RACE = {
    "id": 4,
    "race_name": "Marathon de Brugge",
    "race_date": date(2026, 10, 11),
    "distance_km": 42.20,
    "discipline": "road",
    "objective": "performance",
    "target_time_seconds": 12900,  # 3h35, mid-window; tighten to 12600 (3h30) post-checkpoints
}

# The wizard-generated draft plan to retire before seeding the coach plan.
AUTO_PLAN_ID = 6

# Monday=0 … Sunday=6
MON, TUE, WED, THU, FRI, SAT, SUN = range(7)


@dataclass(frozen=True)
class Session:
    """One planned session within a week, anchored to a weekday offset."""

    offset: int  # 0=Monday … 6=Sunday
    sport: str  # running | trail_running | strength_training
    intensity: str  # easy | moderate | hard | race
    title: str
    description: str
    duration_min: int | None = None
    distance_km: float | None = None


@dataclass(frozen=True)
class Week:
    """A training week anchored on its Monday date."""

    label: str
    monday: date
    sessions: tuple[Session, ...]


# Reusable building blocks ----------------------------------------------------

RENFO_B = Session(
    MON,
    "strength_training",
    "easy",
    "Renfo B — gainage & prévention",
    "20 min, 3 tours : planche frontale 45-60'' · planche latérale 30''/côté · "
    "superman 12 · pont fessier 15 · équilibre unipodal yeux fermés 30''/jambe · "
    "montées de mollets sur marche 15/jambe. Non négociable : tient la posture au km 32.",
    duration_min=20,
)

RENFO_A = Session(
    MON,
    "strength_training",
    "easy",
    "Renfo A — force jambes (allégé)",
    "2 tours (version allégée) : squats 12 · fentes marchées 8/jambe · "
    "soulevé de terre jambes tendues 10 · chaise contre le mur 45''. "
    "Uniquement semaines 10-12 (sans trail vallonné).",
    duration_min=15,
)


def build_weeks() -> list[Week]:
    """Return the full plan, week by week, faithful to spec 03.

    Returns:
        Ordered list of weeks from the transition through race week.
    """
    return [
        Week(
            "Phase 0 — Transition (sem. A)",
            date(2026, 6, 8),
            (
                RENFO_B,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 40'",
                    "Endurance fondamentale 5'45-6'15/km, FC 128-145. Reprise en douceur après la pause.",
                    duration_min=40,
                ),
                Session(
                    WED,
                    "trail_running",
                    "easy",
                    "Club trail (souplesse)",
                    "Sortie club en souplesse, pur aérobie. Reprise progressive obligatoire.",
                    duration_min=60,
                ),
                Session(
                    THU,
                    "running",
                    "easy",
                    "Footing EF 50'",
                    "Endurance fondamentale souple. Pas de VMA dure en transition.",
                    duration_min=50,
                ),
                Session(
                    SUN,
                    "trail_running",
                    "easy",
                    "Trail club tranquille",
                    "Sortie longue club tranquille, FC < 150 en montée si possible. ~35 km sur la semaine.",
                    duration_min=75,
                ),
            ),
        ),
        Week(
            "Phase 0 — Transition (sem. B)",
            date(2026, 6, 15),
            (
                RENFO_B,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 50'",
                    "Endurance fondamentale. Volume cible ~40 km sur la semaine.",
                    duration_min=50,
                ),
                Session(
                    WED,
                    "trail_running",
                    "moderate",
                    "Club trail (modéré)",
                    "Sortie club modérée. Alternative : la touche de vitesse passe au jeudi.",
                    duration_min=70,
                ),
                Session(
                    THU,
                    "running",
                    "moderate",
                    "8×30''/30'' léger",
                    "20' EF + 8×(30'' allure soutenue / 30'' récup) léger + 10' EF. Réveil neuromusculaire, sans forcer.",
                    duration_min=40,
                ),
                Session(
                    SUN,
                    "trail_running",
                    "moderate",
                    "Trail club 1h30-1h45",
                    "Sortie longue club. 📲 Envoyer les stats Garmin en fin de transition pour valider les zones.",
                    duration_min=100,
                ),
            ),
        ),
        # ---- Bloc 1 — Développement général (sem. 1-4) ----
        Week(
            "Bloc 1 — sem. 1",
            date(2026, 6, 22),
            (
                RENFO_B,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 45'",
                    "Endurance fondamentale 5'45-6'15/km.",
                    duration_min=45,
                ),
                Session(
                    WED,
                    "trail_running",
                    "hard",
                    "Club trail (côtes = qualité)",
                    "Si séance de côtes/intensité, c'est TA séance de qualité de la semaine "
                    "(côtes = excellent travail VMA/force). Dans ce cas le jeudi devient un footing EF.",
                    duration_min=75,
                ),
                Session(
                    THU,
                    "running",
                    "easy",
                    "Footing EF 45'",
                    "Si club intense la veille → 45' EF (cas par défaut). Sinon : 20' EF + 2×(8×30''/30'') VMA + 10' EF. "
                    "Jamais deux séances dures hors dimanche.",
                    duration_min=45,
                ),
                Session(
                    SUN,
                    "trail_running",
                    "easy",
                    "Trail club ~20 km EF",
                    "Sortie longue club en endurance fondamentale, FC < 150 en montée si possible. ~42 km/semaine.",
                    duration_min=135,
                    distance_km=20,
                ),
            ),
        ),
        Week(
            "Bloc 1 — sem. 2",
            date(2026, 6, 29),
            (
                RENFO_B,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 50'",
                    "Endurance fondamentale.",
                    duration_min=50,
                ),
                Session(
                    THU,
                    "running",
                    "hard",
                    "VMA 10×400 m",
                    "20' EF + 10×400 m à 4'00-4'08/km (>170 bpm), récup 1' + 10' EF.",
                    duration_min=55,
                ),
                Session(
                    SAT,
                    "running",
                    "easy",
                    "Footing EF 45'",
                    "Endurance fondamentale souple.",
                    duration_min=45,
                ),
                Session(
                    SUN,
                    "trail_running",
                    "easy",
                    "Trail club ~20 km EF",
                    "Sortie longue club en EF. ~46 km/semaine.",
                    duration_min=135,
                    distance_km=20,
                ),
            ),
        ),
        Week(
            "Bloc 1 — sem. 3",
            date(2026, 7, 6),
            (
                RENFO_B,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 55'",
                    "Endurance fondamentale.",
                    duration_min=55,
                ),
                Session(
                    THU,
                    "running",
                    "hard",
                    "VMA 6×800 m",
                    "20' EF + 6×800 m à 4'08-4'15/km, récup 1'30 + 10' EF.",
                    duration_min=60,
                ),
                Session(
                    SAT,
                    "running",
                    "easy",
                    "Footing EF 50' + 8 lignes droites",
                    "50' EF + 8 lignes droites (accélérations progressives ~80 m).",
                    duration_min=55,
                ),
                Session(
                    SUN,
                    "trail_running",
                    "easy",
                    "Trail club + extension route (~22 km)",
                    "Trail club + extension route 20-30' EF. ~50 km/semaine.",
                    duration_min=150,
                    distance_km=22,
                ),
            ),
        ),
        Week(
            "Bloc 1 — sem. 4 (assimilation + TEST)",
            date(2026, 7, 13),
            (
                RENFO_B,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 45' + 6 lignes droites",
                    "45' EF + 6 lignes droites.",
                    duration_min=50,
                ),
                Session(
                    THU,
                    "running",
                    "easy",
                    "Footing EF 30' très souple",
                    "Déchargement avant le test.",
                    duration_min=30,
                ),
                Session(
                    SAT,
                    "running",
                    "race",
                    "⭐ TEST 10 KM CHRONO",
                    "Échauffement 20' + 10 km à fond + retour au calme. Lecture : ≤45' → objectif 3h30 "
                    "(AS42 4'58-5'02) · 45-47' → 3h35 (5'05) · >47' → 3h40 (5'12). On écoute le chrono, pas l'ego.",
                    duration_min=70,
                    distance_km=10,
                ),
                Session(
                    SUN,
                    "running",
                    "easy",
                    "Repos ou 40' très souple",
                    "Repos, ou footing très souple. Trail club zappé cette semaine. ~35 km/semaine.",
                    duration_min=40,
                ),
            ),
        ),
        # ---- Bloc 2 — Seuil & allure marathon (sem. 5-8) ----
        Week(
            "Bloc 2 — sem. 5",
            date(2026, 7, 20),
            (
                RENFO_B,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 50'",
                    "Endurance fondamentale.",
                    duration_min=50,
                ),
                Session(
                    THU,
                    "running",
                    "hard",
                    "Seuil 3×8'",
                    "20' EF + 3×8' au seuil (4'40-4'48/km, FC 160-168), récup 2' + 10' EF.",
                    duration_min=55,
                ),
                Session(
                    SAT,
                    "running",
                    "easy",
                    "Footing EF 45'",
                    "Endurance fondamentale.",
                    duration_min=45,
                ),
                Session(
                    SUN,
                    "trail_running",
                    "moderate",
                    "Trail club + 20' soutenus (~21 km)",
                    "Trail club EF + 20 dernières min à allure soutenue régulière. ~48 km/semaine.",
                    duration_min=140,
                    distance_km=21,
                ),
            ),
        ),
        Week(
            "Bloc 2 — sem. 6",
            date(2026, 7, 27),
            (
                RENFO_B,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 55'",
                    "Endurance fondamentale.",
                    duration_min=55,
                ),
                Session(
                    THU,
                    "running",
                    "hard",
                    "Seuil 2×15'",
                    "20' EF + 2×15' au seuil (4'40-4'48/km), récup 3' + 10' EF.",
                    duration_min=70,
                ),
                Session(
                    SAT,
                    "running",
                    "easy",
                    "Footing EF 45'",
                    "Endurance fondamentale.",
                    duration_min=45,
                ),
                Session(
                    SUN,
                    "running",
                    "moderate",
                    "SL route 2h dont 2×15' AS42 (~21 km)",
                    "Sortie longue sur route/plat, 2h dont 2×15' à AS42 (5'00-5'08/km). Première vraie sortie "
                    "spécifique ; le trail club attendra la semaine prochaine. Gels toutes les 30-40 min.",
                    duration_min=120,
                    distance_km=21,
                ),
            ),
        ),
        Week(
            "Bloc 2 — sem. 7",
            date(2026, 8, 3),
            (
                RENFO_B,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 55'",
                    "Endurance fondamentale.",
                    duration_min=55,
                ),
                Session(
                    THU,
                    "running",
                    "hard",
                    "AS21 5×1000 m",
                    "20' EF + 5×1000 m à AS21 (4'45-4'55/km), récup 1'30 + 10' EF.",
                    duration_min=65,
                ),
                Session(
                    SAT,
                    "running",
                    "easy",
                    "Footing EF 50'",
                    "Endurance fondamentale.",
                    duration_min=50,
                ),
                Session(
                    SUN,
                    "trail_running",
                    "moderate",
                    "Trail club + route 2h15 dont 20' AS42 (~23 km)",
                    "Trail club + extension route : 2h15 total dont 20' AS42 sur la partie plate. ~55 km/semaine.",
                    duration_min=135,
                    distance_km=23,
                ),
            ),
        ),
        Week(
            "Bloc 2 — sem. 8 (assimilation)",
            date(2026, 8, 10),
            (
                RENFO_B,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 45' + 8 lignes droites",
                    "45' EF + 8 lignes droites.",
                    duration_min=50,
                ),
                Session(
                    THU,
                    "running",
                    "easy",
                    "Footing EF 45'",
                    "Endurance fondamentale souple.",
                    duration_min=45,
                ),
                Session(
                    SAT,
                    "running",
                    "easy",
                    "Footing EF 35'",
                    "Endurance fondamentale courte.",
                    duration_min=35,
                ),
                Session(
                    SUN,
                    "trail_running",
                    "easy",
                    "Trail club tranquille (~19 km)",
                    "Trail club tranquille, 18-20 km max, pur plaisir. ~40 km/semaine.",
                    duration_min=130,
                    distance_km=19,
                ),
            ),
        ),
        # ---- Bloc 3 — Spécifique marathon (sem. 9-13) ----
        Week(
            "Bloc 3 — sem. 9",
            date(2026, 8, 17),
            (
                RENFO_B,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 55'",
                    "Endurance fondamentale.",
                    duration_min=55,
                ),
                Session(
                    THU,
                    "running",
                    "hard",
                    "AS42 3×10'",
                    "20' EF + 3×10' à AS42 (5'00-5'08/km, FC 150-160), récup 2' + 10' EF.",
                    duration_min=65,
                ),
                Session(
                    SAT,
                    "running",
                    "easy",
                    "Footing EF 50'",
                    "Endurance fondamentale.",
                    duration_min=50,
                ),
                Session(
                    SUN,
                    "running",
                    "moderate",
                    "SL route 2h30 dont 3×15' AS42 (~25 km)",
                    "Sortie longue SUR PLAT (non négociable pour Bruges), 2h30 dont 3×15' à AS42. "
                    "Gels toutes les 30-40 min, hydratation régulière.",
                    duration_min=150,
                    distance_km=25,
                ),
            ),
        ),
        Week(
            "Bloc 3 — sem. 10",
            date(2026, 8, 24),
            (
                RENFO_B,
                RENFO_A,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 55'",
                    "Endurance fondamentale.",
                    duration_min=55,
                ),
                Session(
                    THU,
                    "running",
                    "hard",
                    "AS21 6×1000 m",
                    "20' EF + 6×1000 m à AS21 (4'45-4'55/km), récup 1'30 + 10' EF.",
                    duration_min=70,
                ),
                Session(
                    SAT,
                    "running",
                    "easy",
                    "Footing EF 45'",
                    "Endurance fondamentale. Renfo A allégé cette semaine.",
                    duration_min=45,
                ),
                Session(
                    SUN,
                    "running",
                    "moderate",
                    "SL route 2h40 dont 40' continues AS42 (~27 km)",
                    "Sortie longue sur plat, 2h40 dont 40' continues à AS42. Pic de spécificité.",
                    duration_min=160,
                    distance_km=27,
                ),
            ),
        ),
        Week(
            "Bloc 3 — sem. 11",
            date(2026, 8, 31),
            (
                RENFO_B,
                RENFO_A,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 50'",
                    "Endurance fondamentale.",
                    duration_min=50,
                ),
                Session(
                    WED,
                    "trail_running",
                    "easy",
                    "Club trail EF contrôlé (remplace samedi)",
                    "Reprise du mercredi club en EF contrôlé (FC < 150). Remplace le footing du samedi.",
                    duration_min=60,
                ),
                Session(
                    THU,
                    "running",
                    "hard",
                    "AS42 2×20'",
                    "20' EF + 2×20' à AS42 (5'00-5'08/km), récup 3' + 10' EF.",
                    duration_min=75,
                ),
                Session(
                    SUN,
                    "running",
                    "moderate",
                    "SL route 2h45 dont 2×25' AS42 (~28 km)",
                    "Sortie longue sur plat, 2h45 dont 2×25' à AS42. ~60 km/semaine.",
                    duration_min=165,
                    distance_km=28,
                ),
            ),
        ),
        Week(
            "Bloc 3 — sem. 12 (charnière + SIMULATION)",
            date(2026, 9, 7),
            (
                RENFO_B,
                RENFO_A,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 50'",
                    "Endurance fondamentale.",
                    duration_min=50,
                ),
                Session(
                    WED,
                    "trail_running",
                    "easy",
                    "Club trail EF très contrôlé",
                    "EF très contrôlé, ou repos si jambes lourdes.",
                    duration_min=60,
                ),
                Session(
                    THU,
                    "running",
                    "hard",
                    "Seuil 4×8'",
                    "20' EF + 4×8' au seuil (4'40-4'48/km), récup 2' + 10' EF. Allège si fatigue.",
                    duration_min=60,
                ),
                Session(
                    SUN,
                    "running",
                    "race",
                    "⭐ SIMULATION route plate 2h50 dont 1h AS42 (~30 km)",
                    "Simulation sur route plate, 2h50 dont 1h continue à AS42. Teste TOUT : gels Etixx (marque "
                    "du parcours), tenue, chaussures, petit-déjeuner, départ à l'heure de course. "
                    "C'est ce chrono qui fixe l'objectif définitif.",
                    duration_min=170,
                    distance_km=30,
                ),
            ),
        ),
        Week(
            "Bloc 3 — sem. 13 (dernière grosse semaine)",
            date(2026, 9, 14),
            (
                RENFO_B,
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 50'",
                    "Endurance fondamentale.",
                    duration_min=50,
                ),
                Session(
                    WED,
                    "trail_running",
                    "easy",
                    "Club trail EF contrôlé",
                    "EF contrôlé, FC < 150.",
                    duration_min=60,
                ),
                Session(
                    THU,
                    "running",
                    "hard",
                    "AS42 3×12'",
                    "20' EF + 3×12' à AS42 (5'00-5'08/km), récup 2' + 10' EF.",
                    duration_min=70,
                ),
                Session(
                    SUN,
                    "running",
                    "moderate",
                    "SL 2h30 dont 3×20' AS42 (~26 km)",
                    "Sortie longue, route — ou trail club + extension plate UNIQUEMENT si tu peux y tenir "
                    "tes blocs AS42. 2h30 dont 3×20' AS42.",
                    duration_min=150,
                    distance_km=26,
                ),
            ),
        ),
        # ---- Bloc 4 — Affûtage (sem. 14-16) ----
        Week(
            "Bloc 4 — sem. 14 (affûtage)",
            date(2026, 9, 21),
            (
                RENFO_B,  # dernier Renfo B
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 45'",
                    "Endurance fondamentale.",
                    duration_min=45,
                ),
                Session(
                    WED,
                    "trail_running",
                    "easy",
                    "Club trail (version légère)",
                    "45-50' max en EF, ou footing. Dernier Renfo B lundi, ensuite stop.",
                    duration_min=50,
                ),
                Session(
                    THU,
                    "running",
                    "hard",
                    "AS42 2×15'",
                    "20' EF + 2×15' à AS42 (5'00-5'08/km) + 10' EF.",
                    duration_min=60,
                ),
                Session(
                    SUN,
                    "running",
                    "moderate",
                    "SL route 1h50 dont 30' AS42 (~18 km)",
                    "Sortie longue route en affûtage, 1h50 dont 30' AS42. Volume -30%.",
                    duration_min=110,
                    distance_km=18,
                ),
            ),
        ),
        Week(
            "Bloc 4 — sem. 15 (affûtage)",
            date(2026, 9, 28),
            (
                Session(
                    TUE,
                    "running",
                    "easy",
                    "Footing EF 40'",
                    "Endurance fondamentale.",
                    duration_min=40,
                ),
                Session(
                    THU,
                    "running",
                    "hard",
                    "AS42 3×8'",
                    "20' EF + 3×8' à AS42 (5'00-5'08/km), récup 2' + 10' EF.",
                    duration_min=50,
                ),
                Session(
                    SAT,
                    "running",
                    "easy",
                    "Footing EF 30'",
                    "Pas de club mercredi cette semaine.",
                    duration_min=30,
                ),
                Session(
                    SUN,
                    "running",
                    "easy",
                    "SL 1h10 EF souple sur plat (~12 km)",
                    "Sortie longue souple sur plat. Volume -50%. Fraîcheur avant tout.",
                    duration_min=70,
                    distance_km=12,
                ),
            ),
        ),
        Week(
            "Bloc 4 — sem. 16 (semaine de course)",
            date(2026, 10, 5),
            (
                Session(
                    TUE,
                    "running",
                    "moderate",
                    "30' EF + 4×3' AS42",
                    "30' EF + 4×3' à AS42 (5'00-5'08/km), récup 2'. Touches d'allure, jambes vives.",
                    duration_min=45,
                ),
                Session(
                    THU,
                    "running",
                    "easy",
                    "Footing EF 30' très souple",
                    "Déverrouillage.",
                    duration_min=30,
                ),
                Session(
                    SAT,
                    "running",
                    "easy",
                    "Déverrouillage 20' + 4 lignes droites",
                    "20' déverrouillage + 4 lignes droites. Retrait du dossard (stand Think Pink, 12h-17h). "
                    "Pâtes, hydratation, coucher tôt. Aucune nouveauté le jour J.",
                    duration_min=25,
                ),
                Session(
                    SUN,
                    "running",
                    "race",
                    "🏁 ATHORA BRUGES MARATHON",
                    "Objectif 3h35 (resserrable 3h30 selon simulation). Km 0-10 : 5-7''/km PLUS LENT que la cible. "
                    "Km 10-30 : allure cible, FC < 160, ravito à chaque poste, gel toutes les 40-45 min. "
                    "Km 30-42 : accroche-toi. Attention au vent côtier vers Zeebrugge (abrite-toi en groupe). "
                    "Passages 3h35 : 10 km 50'55 · semi 1h47'25 · 30 km 2h32'40.",
                    duration_min=215,
                    distance_km=42.2,
                ),
            ),
        ),
    ]


def build_plan() -> list[dict]:
    """Flatten the weeks into dated planned-workout rows.

    Returns:
        Rows with keys: planned_date, sport_type, title, description,
        planned_duration_seconds, planned_distance_meters, intensity.
    """
    rows: list[dict] = []
    for week in build_weeks():
        for s in week.sessions:
            rows.append(
                {
                    "planned_date": week.monday + timedelta(days=s.offset),
                    "sport_type": s.sport,
                    "title": s.title,
                    "description": s.description,
                    "planned_duration_seconds": s.duration_min * 60
                    if s.duration_min
                    else None,
                    "planned_distance_meters": round(s.distance_km * 1000, 2)
                    if s.distance_km
                    else None,
                    "intensity": s.intensity,
                }
            )
    rows.sort(key=lambda r: (r["planned_date"], r["sport_type"]))
    return rows


def _sql_literal(value) -> str:
    """Render a Python value as a SQL literal (None → NULL, escape quotes)."""
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


def emit_sql() -> str:
    """Build the idempotent SQL transaction that seeds the plan on prod."""
    rows = build_plan()
    first = min(r["planned_date"] for r in rows)
    last = max(r["planned_date"] for r in rows)

    lines = [
        "-- Seed: Athora Bruges Marathon plan (Fable 5) — spec 03",
        f"-- {len(rows)} planned_workouts for user_id={USER_ID}, {first}..{last}",
        "BEGIN;",
        "",
        "-- 1. Realign the existing race target's goal time (3h35).",
        f"UPDATE race_targets SET objective={_sql_literal(RACE['objective'])}, "
        f"target_time_seconds={RACE['target_time_seconds']}, "
        f"distance_km={RACE['distance_km']} "
        f"WHERE id={RACE['id']} AND user_id={USER_ID};",
        "",
        "-- 2. Retire the wizard-generated draft plan + clear the calendar window (idempotent).",
        f"DELETE FROM planned_workouts WHERE user_id={USER_ID} "
        f"AND planned_date BETWEEN '{first}' AND '{last}';",
        f"DELETE FROM training_plans WHERE id={AUTO_PLAN_ID} AND user_id={USER_ID};",
        "",
        "-- 3. Insert the coach sessions.",
        "INSERT INTO planned_workouts "
        "(user_id, planned_date, sport_type, title, description, "
        "planned_duration_seconds, planned_distance_meters, intensity) VALUES",
    ]
    values = []
    for r in rows:
        values.append(
            "  ("
            f"{USER_ID}, "
            f"'{r['planned_date']}', "
            f"{_sql_literal(r['sport_type'])}, "
            f"{_sql_literal(r['title'])}, "
            f"{_sql_literal(r['description'])}, "
            f"{_sql_literal(r['planned_duration_seconds'])}, "
            f"{_sql_literal(r['planned_distance_meters'])}, "
            f"{_sql_literal(r['intensity'])}"
            ")"
        )
    lines.append(",\n".join(values) + ";")
    lines += ["", "COMMIT;", ""]
    return "\n".join(lines)


def emit_csv() -> str:
    """Build a CSV matching the /planned-workouts/import endpoint shape."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(
        [
            "date",
            "sport_type",
            "title",
            "description",
            "duration_minutes",
            "distance_km",
            "intensity",
        ]
    )
    for r in build_plan():
        w.writerow(
            [
                r["planned_date"].isoformat(),
                r["sport_type"],
                r["title"],
                r["description"],
                int(r["planned_duration_seconds"] / 60)
                if r["planned_duration_seconds"]
                else "",
                r["planned_distance_meters"] / 1000
                if r["planned_distance_meters"]
                else "",
                r["intensity"],
            ]
        )
    return out.getvalue()


def emit_summary() -> str:
    """Human-readable counts for a quick sanity check (no side effects)."""
    rows = build_plan()
    by_sport: dict[str, int] = {}
    by_intensity: dict[str, int] = {}
    for r in rows:
        by_sport[r["sport_type"]] = by_sport.get(r["sport_type"], 0) + 1
        by_intensity[r["intensity"]] = by_intensity.get(r["intensity"], 0) + 1
    first = min(r["planned_date"] for r in rows)
    last = max(r["planned_date"] for r in rows)
    weeks = build_weeks()
    lines = [
        f"Plan Marathon de Bruges — {len(rows)} séances, {first} → {last} ({len(weeks)} semaines)",
        f"  par sport     : {by_sport}",
        f"  par intensité : {by_intensity}",
        "",
    ]
    for wk in weeks:
        lines.append(f"  {wk.monday} {wk.label} — {len(wk.sessions)} séances")
    return "\n".join(lines)


def main() -> None:
    """Parse args and print the requested representation."""
    parser = argparse.ArgumentParser(description="Seed the Bruges marathon plan.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--sql", action="store_true", help="emit idempotent SQL (default)"
    )
    group.add_argument("--csv", action="store_true", help="emit CSV (import shape)")
    group.add_argument("--summary", action="store_true", help="print counts only")
    args = parser.parse_args()

    if args.summary:
        print(emit_summary())
    elif args.csv:
        sys.stdout.write(emit_csv())
    else:
        sys.stdout.write(emit_sql())


if __name__ == "__main__":
    main()
