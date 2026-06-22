---
tags:
  - projet
  - marathon
  - training
  - nutrition
  - hills-run
  - recettes-app
created: 2026-06-08
updated: 2026-06-08
status: active
type: projet
project: hillsrun
race_date: 2026-10-12
race_type: marathon route (42.195 km)
---

# Préparation Marathon route — 12 octobre 2026

## Objectif

Préparer un marathon route le **12 octobre 2026** via une application personnelle
qui combine **plan d'entraînement** (basé sur données Garmin) et **plan de nutrition**
(recettes quotidiennes adaptées aux séances et compatibles repas familiaux : 2 adultes
+ 1 enfant de 7 ans).

## Décisions cadres (validées 2026-06-08)

| Question | Décision |
|---|---|
| Type de course | **Marathon route** (42,195 km, bitume) |
| Architecture | **Réveiller + connecter les 2 apps existantes** (HillsRun + RecettesApp) |
| Recettes | **Génération IA à la demande** (agent Claude → validation macros Open Food Facts) |

## Contrainte n°1 — le calendrier d'entraînement prime

> Aujourd'hui = 8 juin. Marathon = 12 octobre → **18 semaines**.
> Un bloc marathon de 16 semaines **démarre le ~22 juin**.

Le moteur d'entraînement doit produire un plan exploitable d'ici **~10 jours**.
La nutrition peut suivre : on peut courir avec le plan pendant qu'on construit les recettes.

## Les 4 chantiers (ordre : A → D → B → C)

> Entraînement complet d'abord (statique **A** puis adaptatif **D**), nutrition ensuite (**B** puis **C**).

### Chantier A — Adapter le moteur HillsRun au marathon route ⏳ PRIORITÉ
Le moteur `src/training/` (pipeline 9 étapes) est orienté trail (D+, technique, ultra).
Adaptations route nécessaires (points de contact isolés, code propre) :
- **Discipline `road` + catégorie `road_marathon`** (models + race_classifier)
- **Prédicteur d'allure marathon** depuis la VMA (déjà en base, jamais utilisée) — NOUVEAU module
- **Séances route** : allure marathon spécifique (MPR), seuil, VMA/fractionné ; retrait COT/DESC
- **Sortie longue** plafonnée ~32-35 km (vs cap trail 80 km) + allures route
- **sport_type = `road_running`** (vs `trail_running` codé en dur)
- **DB** : colonne `discipline` sur `race_targets`

### Chantier D — Coach adaptatif (plan réagit aux données Garmin réelles)
Fait réagir le plan à la réalité, en s'appuyant sur des données déjà en base (readiness, HRV, sommeil, activités, ACWR).
- **Niveau A** : coach quotidien GO / PRUDENCE / REPOS (règles + agent IA), recommandation non destructive
- **Niveau B** : réconciliation hebdo planifié↔réalisé → ajuste volume/intensité des semaines suivantes
- Démarrer par D1+D2 (coach quotidien), risque nul. → voir [[Chantier D - Coach Adaptatif - Design]]
- Sera nourri par la recherche approfondie en cours (seuils evidence-based)

### Chantier B — Pont entraînement ↔ nutrition
Nouvelle route HillsRun :
`GET /api/v1/nutrition/daily-needs?date=…`
→ kcal cible + macros (P/G/L) + contexte séance du jour.
Calcul : BMR (body_composition Garmin) × facteur activité + kcal séance (via TSS/durée).

### Chantier C — Génération IA des recettes (RecettesApp)
- Modèle Prisma **`FamilyProfile`** (membres, allergies, aversions, portion enfant)
- Server Action **`generateDailyRecipe`** → API Claude (Sonnet 4.6 qualité / Haiku 4.5 coût)
  en **tool use structuré** (JSON ingrédients + macros)
- **Garde-fou** : revalidation des macros annoncées contre Open Food Facts (proxy existant)

## Séquencement

```
Sprint 0 (cette semaine)  → Chantier A → plan généré → DÉMARRAGE COURSE le 22 juin
Sprint 1 (post-A)         → Chantier D — coach adaptatif (D1+D2 quotidien, puis D3+D4 hebdo)
Sprint 2                  → Chantier B — pont nutrition (besoins du jour)
Sprint 3                  → Chantier C — recettes IA + profil famille
```

## Agents spécialisés ?

**Agents IA dans l'app (runtime) — utile :**
- 🟢 Agent « Recette du jour » — central, c'est le besoin
- 🟡 Agent « Coach adaptatif » (optionnel) — lit readiness/HRV/sommeil Garmin et ajuste la séance

**Sous-agents Claude Code (dev) — à doser :** 2 max (backend-training Python, nutrition-app Next.js),
et seulement si friction. Ne pas investir dans l'outillage avant que le plan d'entraînement tourne.

## Profil athlète figé (2026-06-08)

| Champ | Valeur |
|---|---|
| Niveau | intermédiaire |
| Objectif | sub-3h30 (~4:58/km) — cohérent avec VMA (83 % VMA) |
| VMA | 14,5 km/h |
| FC max / repos | 188 / 56 bpm |
| Course | Marathon de Brugge, 2026-10-12, route plate (D+ ≈ 0) |
| Semaine | mar EF · mer RMU · jeu spécifique · sam EF · dim longue (4 runs + RMU) |
| `day_preferences` (ISO) | `{ "long_run": 7, "quality": [4], "strength": 3 }` |
| Salle | aucune (RMU au poids du corps — déjà OK dans le catalogue) |

## État — Sprint 0

- ✅ Spec auto-portée : `specs/02-road-marathon-adaptation.md` — **durcie après audit** (commit 3fcba12)
- ✅ Branche `feat/road-marathon-engine` + file Ralph (7 tâches) poussées sur `origin`
- ✅ Audit Chantier A : corrigé enum+templates MPR ensemble (évite ValueError), fallback VDOT si VMA absente, allure facile/récup bornée FC Z2, variantes de longue marathon, tests au niveau fonctions pures, `wake-up.sh` durci (push par lot, garde-anti-blocage, notif de fin)
- ✅ **Tâche #7** : seed de mon profil + course Brugge + génération de MON plan réel → export `specs/mon-plan-marathon.md`
- ✅ **Run unique A + D** (11 tâches) : Sprint A (1-7) puis Sprint D coach adaptatif (8-11, D4 propose-only). Spec `03-adaptive-coach.md`
- ✅ **Recherche evidence-based** intégrée (voir [[recherche-marathon-ajustement-dynamique]]) : règle HRV-baseline, ACWR rétrogradé (contesté), correction taper de A (intensité maintenue)
- ⏳ **Ce soir (Mac)** : `git checkout feat/road-marathon-engine && pull`, `brew install jq`, `sh .claude/ralph-tasks/wake-up.sh`
- ⚠️ **Post-merge manuel** : appliquer `sql/11` sur Neon + réplica NAS (migrations à la main) ; suivi frontend (sélecteur discipline dans le wizard) = mini-PR séparée
- Décisions figées : pace model dérivé VMA, `MPR`, `COT`/`DESC` exclues route, cap longue 35 km, `sport_type=road_running`

## Repos & code

- HillsRun : `~/projects/HillsRun` (moteur : `src/training/`, 11 modules)
- RecettesApp : `~/projects/recettes`

## Liens
- [[hillsrun]] — projet HillsRun
- [[Training Plan - Architecture]] — architecture du moteur de plans
- [[recettes-app]] — projet RecettesApp
