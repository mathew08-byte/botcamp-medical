# syntax=docker/dockerfile:1

########## Builder ##########
FROM python:3.11-slim AS builder
WORKDIR /w
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --upgrade pip && pip wheel --wheel-dir /wheels -r requirements.txt

########## Runtime ##########
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Create non-root user
RUN useradd -m -u 10001 botuser

# Install runtime deps
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*

# Copy application
COPY . /app

EXPOSE 8000
USER botuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:8000/ready || exit 1

CMD ["python", "server.py"]

