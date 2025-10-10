# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder

ENV POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl git && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* requirements.txt* /app/

RUN if [ -f requirements.txt ]; then pip install --upgrade pip && pip install -r requirements.txt; fi \
 || (pip install --upgrade pip poetry && poetry install --no-root --only main)

COPY . /app

# Optionally run tests/lint here if desired in build stage

FROM python:3.11-slim AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN useradd -ms /bin/bash botuser

COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

# Healthcheck hits /ready on port 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD curl -fsS http://localhost:8000/ready || exit 1

EXPOSE 8000

USER botuser

CMD ["python", "server.py"]


