---
tags:
  - projet
  - runbook
  - hills-run
  - ralph
created: 2026-06-08
type: runbook
project: hillsrun
---

# Runbook — Lancement du run autonome (Mac, ce soir)

> Run unique **A + D** (11 tâches) sur la branche `feat/road-marathon-engine`.
> Sprint A = moteur route + génération de mon plan. Sprint D = coach adaptatif.

## 0. Pré-requis (à vérifier une fois)

```bash
jq --version          # requis par la boucle Ralph — sinon: brew install jq
claude --version       # Claude CLI installé
uv --version           # gestionnaire Python du backend
```

Variables DB nécessaires à la tâche #7 (seed + génération de mon plan) — doivent être
dans l'environnement ou un `.env` du projet (mêmes que d'habitude) :
`POSTGRES_HOST/PORT/DB/USER/PASSWORD`, `GARMIN_TOKEN_KEY`.

## 1. Récupérer la branche

```bash
cd ~/chemin/vers/HillsRun           # <-- adapter au chemin du clone sur le Mac
git fetch origin
git checkout feat/road-marathon-engine
git pull
```

Vérifier que tout est là :
```bash
ls specs/02-road-marathon-adaptation.md specs/03-adaptive-coach.md
jq '.tasks | length' .claude/ralph-tasks/tasks.json     # doit afficher 11
```

## 2. Lancer la boucle autonome

```bash
sh .claude/ralph-tasks/wake-up.sh
```

La boucle pioche la tâche 1 → code → `uv run pytest` + `ruff` → commit → tâche
suivante… jusqu'à la 11. Elle **push après chaque lot**, s'arrête seule si blocage
(3 itérations sans progrès) et **notifie** à la fin.

- ⏹️ **Ctrl+C** pour arrêter à tout moment.
- 🔁 Reprise : relancer `sh .claude/ralph-tasks/wake-up.sh` (elle repart à la 1re tâche non terminée).

## 3. Ordre des tâches

| # | Lot | Nature |
|---|---|---|
| 1-6 | Moteur route (discipline, allures VMA, longue, catalogue, wiring, DB+API+PR) | code |
| 7 | Seed mon profil + génère **mon plan** → `specs/mon-plan-marathon.md` | code |
| 8 | D1 — coach quotidien HRV (verdict GO/EASE/REST) | non destructif |
| 9 | D2 — couche agent IA du verdict | non destructif |
| 10 | D3 — réconciliation planifié↔réalisé | lecture seule |
| 11 | D4 — ajustement hebdo | **propose-only** |

## 4. Au réveil

```bash
git log --oneline -15                         # voir les commits par lot
cat .claude/ralph-tasks/progress.txt          # apprentissages / là où ça a calé
cat specs/mon-plan-marathon.md                # MON plan généré
gh pr view --web                              # relire la PR
```

## 5. Étapes manuelles post-merge (l'agent n'y touche pas)

Appliquer les migrations à la main sur la base :
```bash
# Neon (prod) + réplica NAS
psql "$NEON_URL" -f sql/11_road_marathon.sql
psql "$NEON_URL" -f sql/12_daily_recommendations.sql
ssh nas "psql -h localhost -U garmin -d garmin_connect -f .../sql/11_road_marathon.sql"
```

Suivis séparés (mini-PR) : sélecteur **discipline** dans le wizard frontend ; carte
**« Recommandation du jour »** ; wiring du verdict HRV dans le cron de sync 05:00.

## Liens
- [[Marathon Route - Plan Projet]]
- [[Chantier D - Coach Adaptatif - Design]]
- [[recherche-marathon-ajustement-dynamique]]
