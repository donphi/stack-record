# ============================================================================
# FILE: Dockerfile
# PURPOSE: Lightweight container for JSON-LD extraction from SQLite
# NOTE: No GPU needed — this is pure IO + serialization
# ============================================================================
FROM python:3.12-slim

LABEL maintainer="kg-extractor"
LABEL description="Extract JSON-LD knowledge graph from SQLite + YAML schema"

# Why --no-install-recommends: keeps image small (~150MB)
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ /app/scripts/
COPY config/ /app/config/

# data/ and output/ are mounted at runtime via docker-compose
CMD ["python3", "scripts/extract.py"]
