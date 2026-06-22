---
tags:
  - projet
  - roadmap
  - planning
  - hills-run
created: 2026-02-28
updated: 2026-02-28
status: active
type: projet
project: hillsrun
---

# HillsRun — Roadmap

## Etat des lieux (28 février 2026)

Le **MVP est complet et déployé** : dashboard, calendrier, sync Garmin, plans d'entraînement, coaching, PWA. L'app est live sur Vercel (frontend) et Railway (backend) avec Neon PostgreSQL.

### Ce qui est fait

| Fonctionnalité | Statut |
|---|---|
| Dashboard (readiness, résumé hebdo, calendrier, VMA) | ✅ |
| Sync Garmin (5 catégories, incrémental, cron NAS) | ✅ |
| Détail activité (métriques, splits, similaires, renommage) | ✅ |
| Calendrier planifié (CRUD, import CSV, templates) | ✅ |
| Plans d'entraînement (génération, wizard, vue semaine) | ✅ |
| Tendances (8 graphiques Plotly) | ✅ |
| Coaching (codes invitation, vue multi-athlètes) | ✅ |
| Auth (Better-Auth email/password, MFA Garmin) | ✅ |
| PWA (Serwist service worker) | ✅ |
| Endpoint nutrition pour RecettesApp | ✅ |
| Tests backend (13 fichiers, training complet) | ✅ |
| Réplica NAS en lecture seule | ✅ |

### Ce qui reste des specs existantes

| Spec | Statut | Effort |
|---|---|---|
| 01 - Tests backend | ✅ Fait | — |
| 02 - Tests frontend | ⚠️ 20% (2 fichiers sur ~9) | 2-3h |
| 03 - Fix scheduler DB | ✅ Fait (sql/07) | — |
| 04 - Security hardening | ✅ Fait (secret roté) | — |
| 05 - CI/CD GitHub Actions | ❌ Non commencé | 1.5h |
| 06 - Intégration RecettesApp | 🎨 Design fait, endpoint prêt, auth partagée à faire | 3-4 jours |

---

## Plan de continuation

### Phase 1 — Solidifier le moteur de plans (priorité haute)

Le plan d'entraînement est la fonctionnalité différenciante. Les [[Training Plan - Architecture#Lacunes identifiées|6 lacunes identifiées]] limitent la qualité des plans générés.

#### 1.1 Exploiter les drapeaux de course
**Fichiers** : `session_catalog.py`, `week_builder.py`
**Effort** : 3-4h

- Injecter des séances de côtes supplémentaires quand `high_dplus = true`
- Ajouter du travail de descente technique quand `technical = true`
- Adapter le volume de dénivelé pour les courses en altitude
- Aujourd'hui ces flags sont calculés mais **jamais utilisés**

#### 1.2 Utiliser les zones FC personnalisées
**Fichiers** : `plan_generator.py`, `session_catalog.py`
**Effort** : 2h

- Les zones Karvonen sont calculées mais pas injectées dans les séances
- Remplacer les zones hardcodées du catalogue par les zones calculées de l'athlète
- Stocker les zones dans `training_plans.generation_params`

#### 1.3 Exploiter l'objectif de course
**Fichiers** : `plan_generator.py`, `week_builder.py`, `session_catalog.py`
**Effort** : 3h

- `objective` (finish/midpack/performance) est stocké mais ignoré
- `finish` : plus de volume en Z2, moins de qualité
- `midpack` : équilibre volume/intensité (comportement actuel)
- `performance` : plus de séances qualité, intensité plus élevée

#### 1.4 Permettre 2+ séances qualité pour avancés/experts
**Fichiers** : `week_builder.py`
**Effort** : 1-2h

- Actuellement limité à 1 séance qualité/semaine (`quality_placed >= 1`)
- Avancé : 2 séances qualité, Expert : 2-3 séances qualité
- Respecter les contraintes de récupération (48h entre Z4-Z5)

#### 1.5 Utiliser `available_slots` JSONB
**Fichiers** : `week_builder.py`
**Effort** : 1-2h

- Le profil athlète a un champ `available_slots` (jours + créneaux)
- Actuellement seul `available_days_per_week` (entier) est utilisé
- Placer les séances sur les jours réellement disponibles

**Total Phase 1 : ~12h**

---

### Phase 2 — Suivi plan vs réalité (priorité haute)

Le plan est généré mais il n'y a **aucun lien entre séances planifiées et activités réalisées**. C'est le chaînon manquant pour que le plan ait de la valeur dans le temps.

#### 2.1 Matching plan ↔ activités
**Effort** : 4-6h

- Auto-matcher une activité Garmin à une `planned_workout` par date + type
- Afficher le statut de complétion sur chaque séance (fait/manqué/modifié)
- Score d'adhérence au plan (% de séances complétées)

#### 2.2 Tableau de bord du plan actif
**Effort** : 3-4h

- Card sur le dashboard : semaine en cours, prochaine séance, adhérence
- Vue condensée de la semaine en cours avec statuts
- Lien rapide vers le détail du plan

#### 2.3 Ajustement dynamique (stretch goal)
**Effort** : 6-8h

- Si l'athlète manque des séances, proposer un réajustement
- Si le TSS réel dépasse le TSS prévu, alerter sur le risque de surcharge
- Nécessite le matching 2.1 comme prérequis

**Total Phase 2 : ~13-18h**

---

### Phase 3 — Enrichir le dashboard santé (priorité moyenne)

Des données Garmin sont collectées mais sous-exploitées côté UI.

#### 3.1 Card résumé quotidien
**Effort** : 2h

- Pas, calories, minutes d'intensité (DailySummary existe déjà côté types/hooks)
- Objectif de pas avec jauge de progression

#### 3.2 Page composition corporelle
**Effort** : 2-3h

- Poids, IMC, masse grasse, masse musculaire (type `BodyComposition` existe)
- Graphiques de tendance dédiés
- Le hook `useBodyComposition` existe déjà

#### 3.3 Tableau de charge d'entraînement
**Effort** : 3h

- Charge chronique vs aiguë (CTL/ATL/TSB)
- Graphique de balance d'entraînement
- Les données `chronic_load` et `acute_load` existent dans `TrainingReadiness`

#### 3.4 Card zones FC
**Effort** : 2h

- Visualiser les 5 zones FC personnalisées
- Distribution du temps par zone sur les dernières semaines

**Total Phase 3 : ~10h**

---

### Phase 4 — Intégration RecettesApp (priorité moyenne)

Le design est fait (spec 06), l'endpoint nutrition est prêt. Reste l'auth partagée et l'intégration côté RecettesApp.

#### 4.1 Auth Better-Auth partagée
**Effort** : 1-2 jours

- Configurer RecettesApp pour utiliser la même base Neon
- Partager la table `user` et les sessions Better-Auth
- Tester le SSO entre les deux apps

#### 4.2 Client HillsRun dans RecettesApp
**Effort** : 1 jour

- Appeler `GET /api/v1/nutrition/daily-goal` depuis RecettesApp
- Afficher l'objectif calorique basé sur l'activité Garmin
- Adapter les recettes aux besoins nutritionnels

**Total Phase 4 : ~3-4 jours**

---

### Phase 5 — Qualité & DevOps (priorité basse, à intercaler)

#### 5.1 Tests frontend
**Effort** : 2-3h

- Hooks : activities, metrics, trends, sync, coaching, training-plans
- Utils : formatters, color helpers
- Composants clés : wizard, calendrier

#### 5.2 CI/CD GitHub Actions
**Effort** : 1.5h

- Frontend : lint + typecheck + build + tests
- Backend : ruff + import-check + pytest
- Déclenchement sur PR vers main

#### 5.3 Rate limiting API
**Effort** : 1h

- Middleware FastAPI-Limiter sur les endpoints publics
- Compléter l'anti-flood existant sur sync

#### 5.4 Logging middleware
**Effort** : 1h

- Logger toutes les requêtes/réponses (masquer les données sensibles)
- Utile pour le debug en production (Railway)

**Total Phase 5 : ~6h**

---

## Priorisation recommandée

```
Phase 1 (Plans)  ████████████ 12h     ← prochaine étape
Phase 2 (Suivi)  █████████████████ 15h ← valeur utilisateur max
Phase 5 (DevOps) ██████ 6h             ← intercaler au fil de l'eau
Phase 3 (Santé)  ██████████ 10h        ← quand les plans sont solides
Phase 4 (Recettes) ████████████████ 3-4j ← quand tout est stable
```

**Recommandation** : commencer par la Phase 1 (améliorer les plans) puis enchaîner sur la Phase 2 (suivi plan versus réalité). La Phase 5 se fait par petits morceaux entre les autres phases. Les Phases 3 et 4 sont indépendantes et peuvent être interchangées selon les priorités.

## Liens

- [[Training Plan - Architecture]] — Architecture détaillée du moteur de plans
- Code : `src/training/` (backend), `web/src/` (frontend)
- Specs existantes : `specs/01-improvements/`
