# Deployment & Runbook

This folder contains Docker, compose, CI/CD workflows, migrations, backup/restore, rollback, and alert tooling.

## Prereqs
- Docker, Docker Compose
- GitHub Actions enabled
- Provider account (Fly.io / Render / Railway)

## Environment
Copy `.env.template` from repo root to `.env` and fill in values. In CI, set GitHub Secrets accordingly.

## Local run
```
cd deployment
docker compose up --build
```

## Health endpoints
- GET /healthz → basic liveness
- GET /ready → checks DB, returns JSON

## Migrations
```
DATABASE_URL=postgres://user:pass@host:5432/db ./migrate.sh
```

## Backup & Restore
```
DATABASE_URL=postgres://... ./backup_postgres.sh
DATABASE_URL=postgres://... ./restore_postgres.sh backup-YYYY-MM-DD.dump
```

## Rollback
```
./rollback.sh ghcr.io/org/repo:previous
```

## Alerts
```
BOT_TOKEN=xxxx SUPER_ADMIN_CHAT_ID=123 ./alert.sh "🚨 Deploy failed; rolling back"
```

## CI/CD
- `.github/workflows/ci.yml` runs lint, tests, builds image
- `.github/workflows/deploy.yml` builds, pushes, runs migrations, polls /ready, rolls back on failure

## Provider deployment
Replace the placeholder deploy step in `deploy.yml` with your provider CLI/API.
