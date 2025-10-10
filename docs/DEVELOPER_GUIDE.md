# Developer Guide

## Repo Overview
- Handlers in `handlers/` and `bot/handlers/`
- Services in `services/` and `bot/services/`
- DB models in `database/models.py` and `models/models.py`
- Health endpoints in `server.py`
- Deployment scripts under `deployment/`

## Local Setup
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd deployment && docker compose up -d
./deployment/migrate.sh
```

## Running
- Bot (polling): `python main.py`
- FastAPI health server: `python server.py` (exposes /healthz, /ready)

## Testing
```
pip install pytest pytest-asyncio
pytest -q
```
- Use sqlite for unit tests; Postgres via compose for integration

## Debugging
- Use `docker compose logs -f`
- DB: `psql` or Adminer at http://localhost:8080
- Redis: `redis-cli`

## Samples
- Upload: use `data/sample_questions.json`

## Tips
- Mock AI/OCR in tests (see `services/ai_parser.py`)
- Use feature flags via env vars for optional providers
