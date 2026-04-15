# lib-registry

Syncs library metadata from `config/*.yaml` into `data/registry.sqlite3`.
Fetches latest versions, dates, descriptions, and stars from PyPI and GitHub.
Writes the JSON data file directly to the site's content directory.

## Usage

```bash
cd tools/lib-registry
docker compose build --no-cache
docker compose run --rm lib-sync
```

### Force a full refresh (bypass change detection)

```bash
docker compose run --rm lib-sync python scripts/sync_registry.py --force
```

Set `GITHUB_TOKEN` in `.env` to avoid rate limits.

## Incremental sync

By default, each library is probed against the stored values in the database.
Only libraries where upstream data has changed (new PyPI version, updated
`pushed_at`, different star count, etc.) are fully re-fetched and written.
Unchanged libraries are skipped entirely, saving API calls and producing
cleaner git diffs.

If no library has been updated for 28 days (configurable in
`config/settings.yaml`), the script automatically escalates to a full
`--force` refresh to self-heal.

## Rolling backups

Every run snapshots `data/registry.sqlite3` and `config/libraries.yaml` into
`backups/` with date-stamped filenames (e.g. `registry.sqlite3.2026-04-14.bak`).
The 5 most recent copies are kept; older ones are pruned automatically.
Backup count is configurable in `config/settings.yaml`.

## Configuration

All runtime tunables live in `config/settings.yaml`:

- `api.github_base_url` / `api.pypi_base_url` — API base URLs
- `requests.timeout_seconds` — HTTP request timeout
- `requests.github_sleep_seconds` — rate-limit delay between GitHub calls
- `backup.max_copies` — number of rolling backups to keep
- `backup.directory` — backup folder name
- `staleness.max_age_days` — days before auto-forcing a full refresh
- `staleness.auto_force` — enable/disable staleness auto-force

## Output

- `data/registry.sqlite3` — updated database
- `data/sync.log` — overwritten each run; lists mode, counts, and failed endpoints
- `data/library-registry.data.json` — JSON copy for reference
- `backups/` — rolling date-stamped backups of DB and config
- `../../content-src/docs/appendices/library-registry/library-registry.data.json` — site data (via volume mount)

## Adding libraries

Edit `config/libraries.yaml`, then re-run the sync.
