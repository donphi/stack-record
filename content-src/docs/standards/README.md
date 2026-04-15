# standards/

This folder holds **standard** notes -- rules and governance for the system.

## Page structure (MDX body)

Every `.mdx` file must **not** contain YAML frontmatter. Use `##` headings in this exact order:

```
## Purpose
## Applies to
## Required fields
## Required sections
## Quality bar
## Failure conditions
```

## JSON sidecar structure (*.meta.json)

**Required fields (build will fail without these):**

| Field | Type | Example |
|-------|------|---------|
| `title` | string | `"Closure Rule"` |
| `description` | string | `"Operational rule for determining note completeness."` |
| `id` | string | `"STD-CLS-0001"` (prefix `STD-`, then code, then number) |
| `type` | string | `"standard"` (must be exactly this) |

**Default values for standards:**

Standards are governance documents. They default to:
- `status`: `"enforced"`
- `domain`: `"standards"`
- `closure_score`: `6` (standards are closed by definition)
- `closure_status`: `"closed"`
- `review_cycle`: `"yearly"`

**Available connection fields:**

| Field | Links to |
|-------|----------|
| `related_notes` | Notes this standard governs |
| `related_standards` | Other standards |
| `superseded_by` / `supersedes` | Version chain |
| `tags`, `status` | Metadata |

Standards are terminal nodes in the graph -- they do not require upward/lateral/applied links.

## Folder navigation (meta.json)

Standards are flat. The `standards/meta.json` lists all pages:

```json
{
  "title": "Standards",
  "icon": "RulerCombine",
  "pages": ["closure-rule", "metadata-schema", "writing-style", "note-quality-bar"]
}
```

## How to add a new standard

1. Create a new folder with the slug name in `standards/` (e.g. `standards/my-standard/`)
2. Copy `_template/example.mdx.template` → `<slug>/index.mdx` and `_template/example.meta.json.template` → `<slug>/index.meta.json`
3. Fill in all fields
4. Write the `.mdx` body
5. Add the slug to `standards/meta.json` `pages` array
6. Run `docker compose up --build` to rebuild and verify
