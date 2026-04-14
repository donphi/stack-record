# tools/lib-registry — Python utility for syncing library metadata.
#
# PURPOSE: Thin container for running sync_registry.py against config/*.yaml.
# OWNS:    Python runtime, requirements install, script execution.
# NOTE:    Mounts config/ and data/ as volumes so the database persists
#          and config is editable from the host.

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/
COPY config/ ./config/

CMD ["python", "scripts/sync_registry.py"]
