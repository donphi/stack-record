# doc-status

Validate, visualize, and inline-edit Stack Record sidecar metadata
(`index.meta.json`) and MDX heading conformity (`index.mdx`).

## How it works

```
content-src/docs/                    config/rules.yaml
  *.meta.json   (sidecars)             (per-type id patterns,
  meta.json     (folder navs)           required keys, enums,
  *.mdx         (headings)              staleness windows,
  _template/*   (per-type contracts)    editable_fields whitelist)
        |                                       |
        v                                       v
   Python pipeline (scanner + validator + writer)
        |
        +---> FastAPI server      (live, editable web app at :8765)
        +---> render_static.py    (output/dashboard.html)
        +---> render_report.py    (output/report.md)
```

The validator produces:
- **Per-note color bucket** (red / amber / gray / green / blue) based on
  declarative conditions in `config/dashboard.yaml`
- **Issue list** per note (missing keys, bad id, bad enum, bad date,
  overdue review, missing required `## heading`, malformed tag)
- **Tree** with bucket roll-up counts per folder
- **Filterable tables** by preset (overdue, drafts, missing, headings,
  open questions, archived)

## Quickstart

```bash
# 1. Live editable dashboard at http://localhost:8765/
docker compose up doc-status

# 2. One-shot static HTML snapshot to ./output/dashboard.html
docker compose run --rm doc-status-static

# 3. Markdown report to ./output/report.md
docker compose run --rm doc-status-report

# 4. Run the test suite (read-only mounts, fixture tree only)
docker compose run --rm test
```

## Maximum control principle

**`config/rules.yaml` and `config/dashboard.yaml` are the single control
surfaces.** Every threshold, regex, color, enum, and editable field lives
in YAML. No Python script defines a default value.

- Add a new note type → add an entry under `note_types` in `rules.yaml`
- Tighten/loosen any id pattern → edit `id_pattern`
- Override the `##` headings the validator demands → set
  `mandatory_headings_override` (otherwise headings are pulled live from
  each type's `_template/example.mdx.template`)
- Change a staleness window → edit `staleness_days`
- Whitelist a new editable field → add to `editable_fields`
- Change a color → edit `dashboard.yaml > color_buckets`
- Add a filter preset → append to `dashboard.yaml > filter_presets`
- Add a markdown report section → append to
  `dashboard.yaml > report_sections`

## Project structure

```
doc-status/
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
├── README.md
├── .gitignore
├── config/
│   ├── rules.yaml          # validation contract
│   ├── dashboard.yaml      # server + colors + filters + report sections
│   └── tests.yaml          # fixture paths + isolation roots + expected issues
├── scripts/
│   ├── config_loader.py    # loads YAML, refuses defaults
│   ├── scanner.py          # fs walk + JSON load + heading regex
│   ├── validator.py        # generic rule engine
│   ├── writer.py           # validated atomic write of one field
│   ├── view_model.py       # tree + filter + bucket roll-ups
│   ├── server.py           # FastAPI live app
│   ├── render_static.py    # one-shot HTML
│   ├── render_report.py    # one-shot Markdown
│   ├── static/styles.css
│   └── templates/
│       ├── base.html.j2
│       ├── tree.html.j2
│       ├── filters.html.j2
│       ├── notes_table.html.j2
│       └── note_row.html.j2
├── tests/
│   ├── conftest.py
│   ├── fixtures/content/   # self-contained mock docs tree
│   ├── unit/
│   │   ├── test_scanner.py
│   │   ├── test_validator.py
│   │   └── test_writer.py
│   ├── integration/
│   │   ├── test_api_read.py
│   │   └── test_api_edit_roundtrip.py
│   ├── isolation/
│   │   └── test_no_external_writes.py
│   └── test_real_templates_parse.py
├── data/                   # cache snapshots (gitignored)
└── output/
    ├── dashboard.html      # generated static export (gitignored)
    └── report.md           # generated markdown report (gitignored)
```

## What you edit

**Only `config/*.yaml`.** Every behavior the tool exhibits is defined
there.

| File | Controls |
| --- | --- |
| `config/rules.yaml`     | Per-type id patterns, required keys, enums, date format, staleness windows, heading conformity policy, tag format, editable_fields whitelist, field types |
| `config/dashboard.yaml` | Server host/port, output paths, color buckets, filter presets, low-closure threshold, report sections, watcher toggle |
| `config/tests.yaml`     | Test fixture paths, isolation roots to hash, expected issue counts per fixture note |

## Three entry points (one codebase)

### Live editable web app

```
docker compose up doc-status
# open http://localhost:8765/
```

- Colored tree (left) + filterable tables (right)
- Click any whitelisted field (status, review_cycle, last_reviewed,
  closure_score, closure_status) to edit it
- HTMX swap re-renders only that row
- Filesystem watcher refreshes the cache when external edits happen
  (e.g. you edit a file directly in Cursor)
- Every successful PATCH writes back to `index.meta.json` atomically,
  preserving 2-space indent and trailing newline

### Static HTML snapshot

```
docker compose run --rm doc-status-static
# open ./output/dashboard.html
```

- Read-only, self-contained, no server, no Docker required to view
- Useful for offline browsing or attaching to a PR

### Markdown report

```
docker compose run --rm doc-status-report
# cat ./output/report.md
```

- Sections defined declaratively in `dashboard.yaml > report_sections`
- Commit-friendly: identical inputs produce identical output

## Test strategy

Three tiers (`tests/unit/`, `tests/integration/`, `tests/isolation/`) all
driven by `config/tests.yaml`.

- **Unit** — scanner, validator, writer in isolation. Writer tests assert
  the on-disk file keeps 2-space indent + trailing newline + sibling MDX
  unchanged.
- **Integration** — `httpx.AsyncClient` against the FastAPI app. The
  round-trip test issues a PATCH, re-reads the file from disk, asserts
  the change persisted, and asserts no other field, note, or MDX changed.
  An invalid PATCH must return 422 AND leave the file byte-identical.
- **Isolation** — SHA-256 hashes every file under
  `tools/kg-builder/`, `tools/kg-extractor/`, `tools/lib-registry/`, and
  the real `content-src/docs/` before and after a full test run. Any
  drift fails the test.

The Docker `test` service mounts everything except the fixture tree as
**read-only**, so isolation is filesystem-enforced — not just trust.

```
docker compose run --rm test
```

## Why we don't depend on `tools/kg-builder/data/kg.sqlite3`

`kg-builder` already extracts every metadata field into SQLite. We
deliberately **do not** read it: coupling means a stale DB shows a stale
dashboard, and edits via doc-status would have to re-trigger kg-builder.
doc-status owns its own lightweight scan (`json.load` + a `^##\s+` regex
— not a real parser), staying single-purpose like every other tool in
`tools/`.
