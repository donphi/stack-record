# ============================================================================
# FILE: Dockerfile
# PURPOSE: Lightweight container for building a SQLite knowledge graph
#          from content-src sidecar metadata, MDX bodies, and library registry
# NOTE: No GPU needed — this is pure IO + serialization
# ============================================================================
FROM python:3.12-slim

LABEL maintainer="kg-builder"
LABEL description="Build SQLite knowledge graph from content-src metadata + MDX bodies"

RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ /app/scripts/
COPY config/ /app/config/

CMD ["python3", "scripts/build_kg.py"]
