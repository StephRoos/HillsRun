# Spec 03 — Plan Marathon de Bruges (transcription fidèle)

> Source de vérité : plan d'entraînement rédigé par Claude (Fable 5) pour l'**Athora Bruges
> Marathon — dimanche 11 octobre 2026**, objectif fenêtre **3h30–3h40**.
> Ce document transcrit le plan en séances datées destinées à la table `planned_workouts`
> de HillsRun (modèle calendrier). Aucun contenu n'est inventé : tout provient du plan source.
> L'encodage exécutable vit dans `scripts/seed_brugge_plan.py` ; ce spec en est le miroir lisible.

## Cible

- **Athlète** : `user_id = 70` (stephaneroos@gmail.com).
- **Course** : `race_targets` « Marathon de Brugge », `2026-10-11`, `discipline='road'`,
  `distance_km=42.20`, `objective='performance'`, `target_time_seconds=12900` (3h35, milieu de
  fenêtre ; resserrable vers 3h30 = 12600 après les rendez-vous vérité).
- **Modèle** : séances `planned_workouts` autonomes (calendrier). Le plan algorithmique
  généré par le wizard (`training_plans` id 6 + ses séances `road_running`) est **remplacé**.

## Conventions d'encodage

`sport_type` (reconnus par le front + valides API) :
- `running` — footings EF, séances de qualité route, sorties longues route.
- `trail_running` — sorties / séances club trail.
- `strength_training` — Renfo A / Renfo B.
- `rest` — non encodé (jour vide = repos dans le calendrier).

`intensity` :
- `easy` — endurance fondamentale, renfo, footings souples.
- `moderate` — sorties longues (avec blocs AS42 dans la description), trail club soutenu.
- `hard` — VMA, seuil, AS21, blocs AS42 en séance de qualité.
- `race` — test 10 km, simulation, marathon.

`planned_date` = lundi d'ancrage de la semaine + offset jour (Lun=0 … Dim=6), calculé par le seed.

## Zones de référence (rappel, pour les descriptions)

| Zone | Allure | FC |
|---|---|---|
| EF | 5'45–6'15/km | 128–145 |
| AS42 (provisoire 3h35) | 5'00–5'08/km | 150–160 |
| AS21 | 4'45–4'55/km | 158–165 |
| Seuil | 4'40–4'48/km | 160–168 |
| VMA | 4'00–4'15/km | >170 |

## Calendrier des semaines (lundis d'ancrage vérifiés)

| Bloc | Sem | Lundi | … Dimanche |
|---|---|---|---|
| Phase 0 — Transition | A | 2026-06-08 | 06-14 |
| Phase 0 — Transition | B | 2026-06-15 | 06-21 |
| Bloc 1 — Développement général | 1 | 2026-06-22 | 06-28 |
| | 2 | 2026-06-29 | 07-05 |
| | 3 | 2026-07-06 | 07-12 |
| | 4 (assimilation + TEST 10 km) | 2026-07-13 | 07-19 |
| Bloc 2 — Seuil & allure marathon | 5 | 2026-07-20 | 07-26 |
| | 6 | 2026-07-27 | 08-02 |
| | 7 | 2026-08-03 | 08-09 |
| | 8 (assimilation) | 2026-08-10 | 08-16 |
| Bloc 3 — Spécifique marathon | 9 | 2026-08-17 | 08-23 |
| | 10 | 2026-08-24 | 08-30 |
| | 11 | 2026-08-31 | 09-06 |
| | 12 (SIMULATION) | 2026-09-07 | 09-13 |
| | 13 | 2026-09-14 | 09-20 |
| Bloc 4 — Affûtage | 14 | 2026-09-21 | 09-27 |
| | 15 | 2026-09-28 | 10-04 |
| | 16 (semaine de course) | 2026-10-05 | 10-11 |

## Règles du coach (reportées en description des séances concernées)

1. Jamais deux séances dures consécutives (club intense ⇒ jeudi en EF, et inversement).
2. Douleur qui modifie la foulée = stop + 2-3 j repos.
3. Séance ratée non rattrapée.
4. Fatigue inhabituelle (FC repos >62-64, sommeil dégradé) ⇒ qualité remplacée par EF.
5. À 49 ans : la récupération EST l'entraînement.
6. Hydratation juillet-août, sorties longues tôt.
7. Aucune nouveauté le jour J (tout validé en semaine 12).
8. Les rendez-vous vérité (test 10 km sem. 4, simulation sem. 12) fixent l'objectif.

## Renforcement

- **Renfo B (gainage/prévention)** — lundi, **toutes les semaines jusqu'à la semaine 14 incluse**,
  20 min. 3 tours : planche frontale 45-60'', planche latérale 30''/côté, superman 12,
  pont fessier 15, équilibre unipodal yeux fermés 30''/jambe, montées de mollets 15/jambe.
- **Renfo A (force jambes)** — **uniquement semaines 10-12**, version allégée 2 tours :
  squats 12, fentes marchées 8/jambe, soulevé de terre jambes tendues 10, chaise 45''.

La liste détaillée séance par séance est encodée dans `scripts/seed_brugge_plan.py`
(fonction `build_plan()`), volontairement unique pour éviter toute divergence spec/seed.
