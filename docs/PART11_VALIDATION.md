# Part 11 — Deployment Validation & Testing Scripts

## Purpose
Validate environment, DB/Redis, bot flows (student/admin/super admin), OCR/AI, persistence, CI/CD, and deployment.

## 1) Environment Validation
- Ensure `.env` has: BOT_TOKEN, DATABASE_URL, REDIS_URL, ADMIN_PASSCODE, SUPER_ADMIN_KEY, OCR/AI keys (optional)
- Run: `python validate_env.py`

## 2) Tests
```
pytest -v
```
Covers role selection, quiz persistence, upload pipeline (mocked), privileges, caching.

## 3) Local Deployment
```
cd deployment
docker compose up --build -d
```
Check logs: `docker compose logs -f`

## 4) Telegram Manual Flows
- Student: /start → select context → Start Quiz → see score
- Admin: /upload → OCR+AI → review/approve
- Super Admin: /dashboard, /alerts, /backup_now

## 5) Telemetry
- /healthz and /ready from `python server.py`
- Snapshots collected by telemetry collector

## 6) Stress Test
```
BOT_TOKEN=... TEST_CHAT_ID=... python scripts/stress_test.py
```

## 7) Security Checks
- Secrets excluded from repo
- Role checks on admin/super_admin handlers
- Optional: `bandit -r .`

## 8) CI/CD
- `.github/workflows/ci.yml` and `deploy.yml` present
- On push to main: image built, migrations run, healthcheck polled

## 9) Acceptance Checklist
- /start responds
- Roles work
- Context persists
- Quiz engine persists score
- Upload pipeline functions
- Admin tools operative
- Super Admin analytics available
- Docker + CI green
- Docs updated
