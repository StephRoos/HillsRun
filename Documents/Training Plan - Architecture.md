---
tags:
  - projet
  - architecture
  - training
  - backend
  - hills-run
created: 2026-02-28
status: active
type: projet
project: hillsrun
---

# Architecture de Génération des Plans d'Entraînement

## Vue d'ensemble

Le moteur de plans d'entraînement est un **pipeline de génération** en 9 étapes, orchestré par `generate_plan()` dans `src/training/plan_generator.py`. Il croise les données Garmin de l'athlète avec son profil et son objectif de course pour produire un plan personnalisé semaine par semaine.

```
Wizard UI (4 étapes)
    │
    ▼
POST /api/v1/training-plans/generate
    │
    ▼
generate_plan() ── transaction DB unique
    │
    ├── 1. Snapshot fitness     ← 7 tables Garmin
    ├── 2. Profil athlète       ← athlete_profiles
    ├── 3. Objectif course      ← race_targets
    ├── 4. Classification       ← logique pure
    ├── 5. Zones FC (Karvonen)  ← calcul
    ├── 6. Durée du plan        ← 6-30 semaines
    ├── 7. Périodisation        ← phases + cycles récup
    ├── 8. Construction semaines ← boucle
    │     ├── Sortie longue progressive
    │     ├── Placement séances (contraintes)
    │     ├── Calcul TSS
    │     └── Validation règle +15%
    └── 9. Sauvegarde DB        ← dual-write pattern
```

## Package `src/training/` - 10 modules

| Module | Rôle |
|---|---|
| `models.py` | Modèles Pydantic, enums (pas d'I/O) |
| `plan_generator.py` | Orchestrateur principal (9 étapes) |
| `fitness_snapshot.py` | Agrège les données Garmin de l'athlète |
| `race_classifier.py` | Catégorise la course + drapeaux |
| `hr_zones.py` | Zones FC via formule de Karvonen |
| `periodization.py` | Découpage en phases + cycles charge/décharge |
| `session_catalog.py` | Catalogue statique de 144 templates de séances |
| `week_builder.py` | Place les séances sur les jours disponibles |
| `long_run.py` | Calcul progressif de la sortie longue |
| `load_calculator.py` | TSS + validation progression +15% |
| `db_operations.py` | CRUD base de données |

## Détail des composants

### 1. Snapshot Fitness (`fitness_snapshot.py`)

`build_fitness_snapshot(pool, user_id)` interroge **7 tables Garmin** :

| Donnée | Source | Fenêtre |
|---|---|---|
| VO2max | activités running | 7 derniers jours |
| FC repos | daily_summary | moyenne 7 jours |
| Poids | body_composition | 30 derniers jours |
| Volume hebdo | activités running | 6 semaines |
| D+ hebdo | activités running | 6 semaines |
| Sortie la plus longue | activités running | 6 semaines |
| Training readiness | training_readiness | moyenne 7 jours |
| VMA | garmin_user | dernière valeur |
| Score sommeil | sleep | moyenne 7 jours |
| HRV | hrv | moyenne 7 jours |

### 2. Classification des courses (`race_classifier.py`)

**Catégories par distance :**
- `trail_court` : < 42 km
- `trail_moyen` : 42-80 km
- `ultra` : 80-160 km
- `ultra_longue` : > 160 km

**Drapeaux :**
- `high_dplus` : ratio D+/km > 60
- `technical` : % technique > 30%
- `is_ultra` : distance >= 80 km
- `high_altitude` : altitude max > 2500 m

### 3. Zones FC (`hr_zones.py`)

Formule de **Karvonen** : `FC_cible = FC_repos + (RFC × %)`

| Zone | % RFC | Usage |
|---|---|---|
| Z1 | 50-60% | Récupération |
| Z2 | 60-70% | Endurance |
| Z3 | 70-80% | Tempo |
| Z4 | 80-90% | Seuil |
| Z5 | 90-100% | VO2max |

Fallbacks : FC_max estimée à `220 - âge` si non renseignée, FC_repos par défaut 60 bpm.

### 4. Périodisation (`periodization.py`)

**4 phases** avec répartition en % du nombre total de semaines :

| Phase | Standard | Ultra |
|---|---|---|
| Base | 30% | 25% |
| Développement | 30% | 30% |
| Spécifique | 25% | 30% |
| Affûtage (taper) | 15% | 15% |

**Cycles de récupération** (fréquence selon l'expérience) :
- Débutant : toutes les 2 semaines
- Intermédiaire/Avancé : toutes les 3 semaines
- Expert : toutes les 4 semaines

**Facteurs de volume par phase :**
- Base : 0.7x | Développement : 0.85x | Spécifique : 1.0x | Taper : 0.5x
- Semaines récup : multiplicateur supplémentaire × 0.6

### 5. Catalogue de séances (`session_catalog.py`)

**9 types de séances :**

| Code | Type | Intensité |
|---|---|---|
| EF | Endurance Fondamentale | Easy |
| SL | Sortie Longue | Easy-Moderate |
| TMP | Tempo | Hard |
| INT | Intervalles | Hard |
| COT | Côtes | Hard |
| DESC | Descente | Moderate |
| REC | Récupération | Easy |
| RMU | Renforcement musculaire | Moderate |
| REST | Repos | - |

**144 templates** = 9 types × 4 niveaux × 4 phases. Chaque template contient : titre, description, sport, intensité, zone FC primaire, fourchette de durée, blocs (échauffement/corps/retour au calme).

**Séances recommandées par phase :**
- Base : EF, SL, REC, RMU
- Développement : + TMP, INT
- Spécifique : + COT, DESC
- Taper : EF, SL, REC uniquement

### 6. Construction des semaines (`week_builder.py`)

**Nombre de séances par niveau :**
- Débutant : 3 | Intermédiaire : 4 | Avancé : 5 | Expert : 6
- Semaines récup : -1 séance

**Algorithme de placement :**
1. Sortie longue placée le week-end (samedi prioritaire, sinon dimanche)
2. Séance qualité (TMP/INT/COT) en semaine (mardi-vendredi), **limitée à 1 par semaine**
3. Remplissage avec EF/REC
4. RMU sur les jours sans course, non adjacents aux séances dures

**Contraintes de scheduling :**
- Pas 2 jours durs consécutifs
- 48h minimum entre séances Z4-Z5
- RMU jamais adjacent à une séance dure

### 7. Sortie longue progressive (`long_run.py`)

**Distances de départ :**
- Débutant : 10 km | Intermédiaire : 15 km | Avancé : 20 km | Expert : 25 km

**Progression hebdomadaire :**
- Débutant : +10% | Intermédiaire : +12% | Avancé : +13% | Expert : +15%

**Plafonds par phase** (% de la distance course) :
- Base : 30% | Développement : 50% | Spécifique : 70% | Taper : 40%
- Plafond absolu : 80 km
- Semaines récup : -40% depuis la baseline

**Allures trail estimées :** débutant 8 min/km → expert 5.5 min/km.

### 8. Calcul de charge (`load_calculator.py`)

**Formule TSS** : `durée_heures × facteur_intensité × facteur_dénivelé`

Facteur dénivelé : `1.0 + (D+ / 1000) × 0.15`

| Type séance | Facteur intensité |
|---|---|
| REST | 0 |
| REC | 30 |
| RMU | 45 |
| EF | 50 |
| SL | 55 |
| DESC | 40 |
| TMP | 70 |
| COT | 75 |
| INT | 85 |

**Règle de progression +15%** : le TSS hebdomadaire ne doit pas augmenter de plus de 15% entre deux semaines non-récup. Si violation, les durées de séances sont réduites proportionnellement.

## Pattern Dual-Write (DB)

Chaque séance d'entraînement crée **2 lignes en base** :

1. **`planned_workouts`** : visible sur le calendrier, liée au plan via `plan_id`
2. **`training_plan_sessions`** : liée à `plan_id` + `week_id` + `planned_workout_id`

Cela permet au calendrier d'afficher les séances du plan à côté des séances manuelles, tout en conservant les métadonnées structurelles (phases, semaines, ordre).

### Schéma DB (5 tables + extension)

```
athlete_profiles ──┐
race_targets ──────┤
                   ▼
           training_plans
                   │
                   ▼
         training_plan_weeks
                   │
                   ▼
       training_plan_sessions ──→ planned_workouts (calendrier)
```

Toutes les FK sont `ON DELETE CASCADE`.

## Frontend

### Wizard de création (4 étapes)

| Étape | Contenu |
|---|---|
| 0 - Profil | Niveau, jours/semaine, FC max/repos, accès côtes/salle |
| 1 - Course | Sélection ou création (nom, date, distance, D+, objectif) |
| 2 - Préférences | Nom du plan, override nb semaines, aperçu fitness |
| 3 - Génération | Récap + lancement, redirection vers le détail |

### Vue détail du plan

- Onglets semaine par semaine (S1, S2, ..., indicateur récup)
- Par semaine : badge phase, badge récup, TSS total, nb séances
- Par séance : jour, badge type (couleurs), titre, description, durée, distance, zone FC, TSS
- Actions : Activer (draft), Terminer (active), Supprimer

### Hooks TanStack Query

11 hooks dans `use-training-plans.ts` couvrant le cycle complet. Les mutations invalident à la fois `["training-plans"]` et `["planned-workouts"]` pour synchroniser le calendrier.

## Lacunes identifiées

> [!warning] Points d'amélioration à considérer

### 1. Zones FC calculées mais non utilisées
`calculate_hr_zones()` est appelé dans l'orchestrateur mais le résultat **n'est jamais injecté** dans les templates de séances. Les séances utilisent les valeurs `hr_zone_primary` codées en dur dans le catalogue.

### 2. Drapeaux de course non exploités
Les flags `high_dplus`, `technical`, `high_altitude` sont classifiés et stockés dans `generation_params` mais **n'influencent pas** la sélection des séances (pas de séances de côtes supplémentaires pour les courses à fort D+, pas de travail de descente technique pour les courses techniques).

### 3. Maximum 1 séance qualité par semaine
`build_week()` limite à 1 séance qualité (TMP/INT/COT). Les athlètes avancés/experts bénéficieraient de 2+ séances qualité par semaine.

### 4. Objectif de course ignoré
Le champ `objective` (finish/midpack/performance) de `RaceTargetInput` est stocké dans `race_targets` mais **jamais utilisé** dans la logique de génération -- il ne modifie ni le volume, ni l'intensité, ni la sélection des séances.

### 5. Pas de validation de `start_date`
Un utilisateur peut définir une date de début dans le passé sans erreur.

### 6. `available_slots` JSONB inutilisé
Le champ `available_slots` de `athlete_profiles` n'est pas exploité par le week builder, qui se base uniquement sur `available_days_per_week` (entier).

## Liens

- [[Training Plan - Améliorations]] *(à venir)*
- Code : `src/training/` (backend), `web/src/app/(dashboard)/training-plan/` (frontend)
- API : `POST /api/v1/training-plans/generate`
- Schéma DB : `sql/08_training_plans.sql`
