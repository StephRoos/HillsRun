---
tags:
  - projet
  - architecture
  - training
  - adaptive
  - hills-run
created: 2026-06-08
status: design
type: projet
project: hillsrun
depends_on: Chantier A (moteur route) mergé
---

# Chantier D — Coach Adaptatif (design)

## Problème

Le plan généré par le moteur est **personnalisé une fois puis figé** : aucune
boucle de rétroaction ne lit les données Garmin après la génération. Le Chantier D
fait **réagir le plan à la réalité** : signaux de forme quotidiens (niveau A) +
réconciliation planifié↔réalisé hebdomadaire (niveau B).

## Données déjà disponibles (rien à synchroniser de neuf)

| Donnée | Table | Usage |
|---|---|---|
| Training readiness (score, chronic/acute load) | `training_readiness` | verdict quotidien + ACWR |
| HRV (quotidien + moyenne 7j) | `hrv` | écart vs baseline |
| Score de sommeil | `sleep` | facteur de fatigue |
| Body battery / stress | `daily_summary` | contexte |
| FC repos | `daily_summary` | dérive vs baseline |
| **Activités réelles** (allure, FC, D+, durée) | `activities` | matching planifié↔réalisé, TSS réel |
| Séances planifiées | `planned_workouts` / `training_plan_sessions` | la cible à comparer |

> ⚠️ **Mis à jour après recherche** (voir [[recherche-marathon-ajustement-dynamique]]) :
> le signal **validé** est la **HRV du matin vs baseline individuelle** (méthode HRV-guided).
> L'**ACWR est contesté** (aucune plage sûre confirmée) → signal **informatif seulement**,
> jamais une règle dure. Garmin Training Readiness = secondaire (non validé indépendamment).

---

## Niveau A — Coach quotidien (à construire en premier)

**Déclencheur** : chaque matin, juste après le cron de sync (déjà 05:00 Europe/Paris).

**Logique**
1. Lire la séance planifiée du jour.
2. Lire les signaux du matin : readiness, HRV vs baseline 7j, sommeil, body battery,
   FC repos vs baseline.
3. Calculer un verdict **GO / PRUDENCE / REPOS**.
4. Produire une **recommandation non destructive** (ne réécrit PAS le plan) :
   - 🟢 GO : séance comme prévu
   - 🟡 PRUDENCE : dégrader (qualité → footing, durée −20-30 %)
   - 🔴 REPOS : repos / récup active, proposer de décaler la qualité plus tard dans la semaine

**Décisions clés**
- **Advisory par défaut** : l'utilisateur accepte/refuse. Bouton « Appliquer » optionnel
  qui swap la séance. Jamais de mutation silencieuse.
- Nouvelle table `daily_recommendations` (date, user_id, verdict, raison,
  modification_suggérée, accepted bool).
- **Deux implémentations possibles du verdict :**
  - *Règles* (socle, **evidence-based**) : **HRV matin lnRMSSD vs baseline individuelle**
    (60j glissants, plage = moyenne ± 0,5 σ, recalcul hebdo). Dans/au-dessus → GO ;
    sous la borne basse → PRUDENCE (dégrade) ; nettement sous (< −1 σ) 2j de suite → REPOS.
    Modificateurs secondaires à la marge seulement (sommeil < 50, FC repos > baseline +5,
    Garmin readiness < 30), jamais d'override d'un REPOS. Bande = anti-thrashing intégré.
  - *Agent IA* (la vraie valeur) : un agent Claude lit les signaux + la séance + le
    contexte récent et **raisonne** : « HRV −12 %, 5 h de sommeil après tes
    intervalles d'hier → transforme ton tempo en 40 min easy ». Sortie structurée
    (verdict + modif + explication). Clé API côté serveur (SDK anthropic Python,
    dans le cron). **C'est ici que l'agent spécialisé justifie pleinement sa place.**

**Surface** : carte « Recommandation du jour » sur le dashboard + notification push matinale.

---

## Niveau B — Réconciliation hebdomadaire (ensuite)

**Déclencheur** : fin de semaine d'entraînement (dimanche soir / lundi matin, cron).

**Logique**
1. **Matcher planifié ↔ réalisé** : pour chaque `planned_workout` de la semaine,
   retrouver l'activité Garmin correspondante (date + type de sport). Calculer la
   compliance : fait ? durée/allure/TSS réels vs prévus.
2. **Charge réelle** : somme du TSS réalisé vs planifié (ACWR **informatif uniquement**, contesté).
3. **Ajuster les semaines suivantes** :
   - réalisé ≪ prévu (séances manquées) → ne pas empiler, garder stable
   - signaux de surcharge soutenus (AMBER/RED répétés + faible compliance) → injecter/allonger la récup
   - régulièrement en avance + frais → progression légèrement accélérée (dans la règle +15 %)
   - VMA/VO2max améliorés → re-snapshot et **recalcul des allures**
4. **Appliquer** : proposer les changements pour validation (toggle « auto-appliquer
   les ajustements mineurs »).

**Nouveaux composants** (package `src/training/adaptive/`)
- `workout_matcher.py` — lie `planned_workouts` ↔ `activities`
- `adherence.py` — compliance + charge réelle + ACWR
- `plan_adjuster.py` — modifie les semaines à venir (réutilise `week_builder`/`load_calculator`)
- Endpoint `POST /api/v1/training-plans/{id}/reconcile` (déclenchement manuel) + cron
- Table `weekly_reconciliations` (plan_id, semaine, tss_planifié, tss_réel, acwr, ajustement)

---

## Architecture & séquencement

```
src/training/adaptive/
├── readiness.py        # niveau A : verdict du jour (règles + agent)
├── workout_matcher.py  # niveau B : planifié ↔ réalisé
├── adherence.py        # niveau B : compliance, TSS réel, ACWR
└── plan_adjuster.py    # niveau B : ajuste les semaines restantes
```

- **D1** : niveau A règles → **D2** : niveau A agent IA → **D3** : niveau B matching/adherence → **D4** : niveau B ajustement.
- **Démarrer par D1+D2** (coach quotidien) : meilleur ratio valeur/effort, risque nul (aucune mutation du plan).

## Garde-fous

- Jamais de mutation sans trace ; advisory par défaut.
- Éviter le **plan thrashing** : changements structurels en **batch hebdo**, pas quotidien (sinon perte de confiance).
- Matching planifié↔réalisé **flou** (un tempo loggé en « course » générique) → tolérance + override manuel.
- ACWR **bruité en début de bloc** (peu d'historique) → garde-fou.
- Ne pas double-compter : un dégrade « readiness » du jour ne doit pas aussi déclencher une pénalité « séance manquée » en hebdo.

## Synergie nutrition (Chantiers B/C)

Le verdict quotidien + la charge réelle alimentent aussi `daily-needs` (Chantier B) :
séance dure réalisée = kcal/glucides relevés ce jour-là. Le coach et la nutrition
partagent le même signal de charge.

## Liens
- [[Marathon Route - Plan Projet]]
- [[Training Plan - Architecture]] — moteur de génération (statique)
