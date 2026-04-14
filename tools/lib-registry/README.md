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

Set `GITHUB_TOKEN` in `.env` to avoid rate limits.

## Output

- `data/registry.sqlite3` — updated database
- `data/sync.log` — overwritten each run; lists failed endpoints
- `data/library-registry.data.json` — JSON copy for reference
- `../../content-src/docs/appendices/library-registry.data.json` — site data (via volume mount)

## Adding libraries

Edit `config/libraries.yaml`, then re-run the sync.
