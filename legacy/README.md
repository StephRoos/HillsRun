# legacy/ — pre-UM880 deployment configs

Kept for reference after the migration to self-hosted UM880 (Coolify). Not used anymore.

- `railway.toml` — backend deploy config when the FastAPI app ran on Railway
  (`api.hillsrun.com`). Replaced by the `api` service in `docker-compose.coolify.yml`.
- `docker-compose.nas.yml` — Postgres read-only replica on the NAS Ugreen, fed by
  Neon logical replication. Obsolete: the primary Postgres now lives in the Coolify
  compose on UM880; Neon has been retired.

Also deprecated (still in `scripts/` for history, no longer run):
- `scripts/setup-replica.sh`, `scripts/check-replica.sh` — Neon → NAS replication setup.

See `docs/DEPLOY-UM880.md` for the current deployment.
