# Contributing to BotCamp Medical

## Coding Standards
- Python 3.11
- Format with `black`; imports with `isort`; lint with `flake8`
- Type hints required for public functions/classes
- Docstrings for public APIs

## Branching & Commits
- `main` = production
- Feature branches: `feature/<slug>`
- Hotfix branches: `hotfix/<slug>`
- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`

## Pull Requests
- 1+ approving review required
- CI must pass (lint + tests)
- Include Alembic migration if DB schema changes
- Add/extend tests for new behavior

## Setup (Dev)
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd deployment && docker compose up -d
./deployment/migrate.sh
pytest -q
```

## Security
- Do not commit secrets
- Use provider/GitHub Secrets for CI/CD

## Release
- Semantic versioning (MAJOR.MINOR.PATCH)
- Tag releases and include notes: breaking changes, features, migrations
