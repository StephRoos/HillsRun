# Déploiement HillsRun sur UM880 (Coolify)

Migration depuis Vercel (frontend) + Railway (backend) + Neon (DB) vers un
hébergement unique self-hosted sur le Minisforum UM880 Pro, via Coolify.

- **Frontend** Next.js 16 → service `web` (Traefik + Cloudflare Tunnel → `hillsrun.com`)
- **Backend** FastAPI → service `api` (**interne**, `http://api:8000`)
- **Base** Postgres 16 → service `db` (primary, **remplace Neon**)
- **Sync** → service `sync` (cron quotidien 06:00 Europe/Paris, remplace le cron du NAS)

Compose de référence : [`docker-compose.coolify.yml`](../docker-compose.coolify.yml).

> Principe : **zéro coupure**. On déploie sur UM880 en parallèle de la prod actuelle,
> on teste, puis on bascule le DNS. Rollback = repointer le DNS sur Vercel/Railway.
> On ne supprime Vercel/Railway/Neon qu'à la toute fin.

---

## Variables d'environnement (à saisir dans Coolify)

| Variable | Exemple / source | Utilisée par |
|----------|------------------|--------------|
| `POSTGRES_USER` | `garmin` | db, api, web |
| `POSTGRES_PASSWORD` | `openssl rand -base64 24` | db, api, web |
| `POSTGRES_DB` | `garmin_connect` | db, api, web |
| `API_KEY` | reprendre la valeur Railway actuelle | api, web, sync |
| `GARMIN_TOKEN_KEY` | reprendre la valeur Railway (clé Fernet) | api |
| `BETTER_AUTH_SECRET` | reprendre la valeur Vercel | web |
| `BETTER_AUTH_URL` | `https://hillsrun.com` | web |
| `NEXT_PUBLIC_BETTER_AUTH_URL` | `https://hillsrun.com` | web (build arg) |
| `LOG_LEVEL` | `INFO` | api |
| `TZ` | `Europe/Paris` | tous |

> `GARMIN_API_KEY` (web) et `API_KEY` (api/sync) **doivent être identiques** — le compose
> mappe déjà `GARMIN_API_KEY: ${API_KEY}`. `DATABASE_URL` et `GARMIN_API_URL` sont
> construits dans le compose, rien à saisir.

Récupérer les valeurs existantes avant de couper quoi que ce soit :
```bash
# Railway (CLI) — variables backend
railway variables          # API_KEY, GARMIN_TOKEN_KEY, POSTGRES_*

# Vercel (CLI) — variables frontend
vercel env pull .env.vercel.bak   # BETTER_AUTH_SECRET, GARMIN_API_KEY, DATABASE_URL...
```

---

## Étape 1 — Migration des données Neon → Postgres UM880

L'ancienne base contient les tables Garmin (raw SQL) **et** les tables Better-Auth (Prisma).
On dump tout, puis on restaure dans le `db` du compose.

### 1.1 Dump depuis Neon (depuis le Mac ou n'importe quelle machine)
```bash
# Connstring Neon (Dashboard Neon → Connection string, role owner)
export NEON_URL='postgresql://USER:PWD@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require'

# Dump complet schéma + données, format custom (compressé, restaurable sélectivement)
pg_dump "$NEON_URL" --no-owner --no-privileges -Fc -f hillsrun_neon.dump
```

### 1.2 Démarrer la stack sur UM880 (sans exposer encore le DNS)
Créer le projet dans Coolify (Étape 2) et lancer un premier déploiement pour que le
service `db` tourne. Vérifier :
```bash
ssh um880 "docker ps | grep -E 'db|api|web'"
```

### 1.3 Restaurer dans le Postgres UM880
```bash
# Copier le dump sur le UM880
scp hillsrun_neon.dump um880:/tmp/

# Identifier le conteneur db de Coolify
ssh um880 "docker ps --format '{{.Names}}' | grep -i db"   # ex: hillsrun-db-xxxx

# Restaurer (adapter le nom du conteneur + POSTGRES_USER/DB)
ssh um880 "docker exec -i <db_container> pg_restore --no-owner --no-privileges \
  -U garmin -d garmin_connect --clean --if-exists < /tmp/hillsrun_neon.dump" \
  < /tmp/hillsrun_neon.dump
```
> Variante simple si `pg_restore` rechigne sur l'ordre des dépendances : faire un dump
> SQL plat (`pg_dump "$NEON_URL" --no-owner --no-privileges -f dump.sql`) puis
> `docker exec -i <db> psql -U garmin -d garmin_connect < dump.sql`.

### 1.4 Vérifier l'intégrité
```bash
ssh um880 "docker exec <db_container> psql -U garmin -d garmin_connect -c '\dt'"
# Doit lister les tables Garmin + les tables Better-Auth (user, session, account...).
ssh um880 "docker exec <db_container> psql -U garmin -d garmin_connect \
  -c 'SELECT count(*) FROM activities;'"
```

---

## Étape 2 — Projet Coolify

1. Coolify → **New Resource → Docker Compose** (ou Application liée au repo GitHub
   `StephRoos/HillsRun`, branche `migrate/um880` puis `main` après merge).
2. **Compose file** : `docker-compose.coolify.yml`.
3. **Build pack** : Docker Compose (Coolify build les services `api` et `web` depuis
   leurs Dockerfile respectifs).
4. Renseigner toutes les variables du tableau ci-dessus dans **Environment Variables**.
5. Connecter le réseau Traefik de Coolify (par défaut pour les apps Coolify).
6. Déployer. Vérifier les healthchecks :
   ```bash
   ssh um880 "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -i hillsrun"
   ```
   `api` et `web` doivent être `healthy`, `db` `healthy`, `sync` `Up`.

---

## Étape 3 — Exposition (Cloudflare Tunnel, PAS de port entrant)

**Architecture réelle** (vérifiée) : la maison n'a **aucun port entrant ouvert** (ni 80
ni 443). Tout passe par un **Cloudflare Tunnel** — `cloudflared` tourne sur le UM880
(process hôte `cloudflared tunnel run --token …`, tunnel id `6b5cb58d-2344-4653-8d0b-ba7723f8ac6d`)
et établit une connexion **sortante** vers Cloudflare. C'est ainsi que ladtc est exposé.
Conséquence : pas de challenge Let's Encrypt HTTP-01 possible (port 80 fermé) — le
**certificat est servi par l'edge Cloudflare** (Universal SSL), pas par l'origine.

Trois éléments à configurer :

1. **Coolify** — `docker_compose_domains` de l'app (mapping service → domaine), via
   l'API `PATCH /applications/{uuid}` avec un **tableau** :
   ```json
   {"docker_compose_domains":[{"name":"web","domain":"https://hillsrun.com,https://www.hillsrun.com"}]}
   ```
   Coolify génère alors les routers Traefik. NE PAS écrire de labels Traefik à la main
   dans le compose (conflit). `api`/`db`/`sync` n'ont pas de domaine → internes.

2. **Ingress du tunnel** — ajouter les hostnames sur le tunnel UM880, **vers l'entrypoint
   HTTPS de Traefik** (et non `http://localhost:80`, qui provoque une boucle de
   redirection http→https) :
   ```
   hillsrun.com      → https://localhost:443   (originRequest: noTLSVerify=true, httpHostHeader=hillsrun.com)
   www.hillsrun.com  → https://localhost:443   (idem httpHostHeader=www.hillsrun.com)
   ```
   API : `PUT /accounts/{acc}/cfd_tunnel/{tunnel}/configurations` (renvoyer la config
   ingress complète, hostnames insérés avant le catch-all `http_status:404`).

3. **DNS Cloudflare** — `hillsrun.com` et `www` en **CNAME proxifié** vers
   `6b5cb58d-2344-4653-8d0b-ba7723f8ac6d.cfargotunnel.com` (PAS un A record vers l'IP
   publique → donnerait un 522). SSL/TLS mode **Full**.

> Note API Cloudflare : changer l'enregistrement **apex** de A → CNAME peut renvoyer un
> `10405` trompeur (réessayer / recréer). `api.hillsrun.com` n'est plus exposé : supprimer
> son CNAME Railway + le TXT `_railway-verify` à la fin.

---

## Étape 4 — Smoke tests (avant bascule DNS finale)

```bash
# 1. Le front répond
curl -I https://hillsrun.com            # 200 + headers de sécurité (CSP, HSTS...)

# 2. Health API interne (depuis le UM880)
ssh um880 "docker exec <web_container> wget -qO- http://api:8000/health"

# 3. Sync manuel (depuis le UM880, réseau interne)
ssh um880 "docker exec <sync_container> sh -c 'curl -s -X POST \
  -H \"X-API-Key: \$API_KEY\" http://api:8000/api/v1/sync/trigger'"
```
Dans le navigateur : login Better-Auth, dashboard, graphiques Plotly, calendrier,
mode coach. Vérifier qu'aucune requête ne tape `api.hillsrun.com` (onglet Network).

---

## Étape 5 — Bascule finale & nettoyage

1. Confirmer que `hillsrun.com` sert bien l'app UM880 (DNS propagé).
2. **Railway** : supprimer le service / projet HillsRun (ou le mettre en pause).
3. **Vercel** : supprimer le projet `web` (ou délier le repo).
4. **DNS** : supprimer `api.hillsrun.com` (CNAME Railway) + le public hostname tunnel.
5. **NAS Ugreen** : arrêter le réplica (`docker compose -f legacy/docker-compose.nas.yml down`)
   et désactiver le cron sync NAS (remplacé par le service `sync`).
6. **Neon** : dernier `pg_dump` d'archive, puis fermer le projet Neon.
7. Re-figer le projet (commit `docs: re-freeze — migrated to UM880`).

### Rollback (si problème avant l'étape 5)
Repointer le DNS `hillsrun.com` sur Vercel et `api.hillsrun.com` sur Railway (intacts).
Aucune donnée perdue : Neon reste la source tant qu'on ne l'a pas fermée.

---

## Sauvegardes (post-migration)

La DB n'est plus managée par Neon → prévoir un backup, aligné sur le homelab (B2) :
```bash
# Cron sur UM880 (ou tâche planifiée Coolify) — dump quotidien vers Backblaze B2
docker exec <db_container> pg_dump -U garmin garmin_connect -Fc \
  | rclone rcat b2:backups/hillsrun/db-$(date +\%F).dump
```
