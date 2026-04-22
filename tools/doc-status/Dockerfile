# ============================================================================
# FILE: Dockerfile
# PURPOSE: Lightweight container for the doc-status dashboard. Serves a
#          FastAPI + Jinja2 + HTMX web app that scans content-src/docs/,
#          validates every index.meta.json against per-type templates and
#          rules, and writes back whitelisted edits.
# NOTE: No GPU, no native deps — pure Python.
# ============================================================================
FROM python:3.12-slim

LABEL maintainer="doc-status"
LABEL description="Validate, visualize, and edit Stack Record sidecar metadata"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ /app/scripts/
COPY config/ /app/config/

EXPOSE 8765

CMD ["python3", "-m", "uvicorn", "scripts.server:app", "--host", "0.0.0.0", "--port", "8765"]
