# maps/

This folder holds **map** notes -- navigation and orientation pages (MOCs) that connect related knowledge.

## Page structure (MDX body)

Every `.mdx` file must **not** contain YAML frontmatter. Use `##` headings in this exact order:

```
## What this map is
## Why this matters
## Where this fits
## Structure
## What this map helps answer
## Notes in this map
## Gaps and open loops
## Review
```

The `## Notes in this map` section must use `[[wiki links]]` to every child note. The `## Structure` section should include a tree or diagram showing the hierarchy.

## JSON sidecar structure (*.meta.json)

**Required fields (build will fail without these):**

| Field | Type | Example |
|-------|------|---------|
| `title` | string | `"Learning Map"` |
| `description` | string | `"Top-level orientation map connecting the four child maps."` |
| `id` | string | `"MAP-LEARN-0001"` (prefix `MAP-`, then code, then number) |
| `type` | string | `"map"` (must be exactly this) |

**Mandatory for knowledge graph completeness:**

| Field | Rule | Why |
|-------|------|-----|
| `children` | >= 1 entry | Maps must have children (D dimension) |
| `review_cycle` + `last_reviewed` | both set | Maintenance (M) |

**All available connection fields:**

| Field | Links to |
|-------|----------|
| `children` | Notes this map organizes |
| `related_notes` | Peer notes |
| `related_methods` | Method notes |
| `related_systems` | System notes |
| `related_projects` | Project notes |
| `open_questions` | Open questions list |
| `tags`, `domain`, `status` | Metadata |

## Folder navigation (meta.json)

Maps are flat (no sub-folders). The `maps/meta.json` lists all map pages:

```json
{
  "title": "Maps",
  "icon": "Map",
  "pages": ["learning-map", "domain-map", "method-map", "system-map", "open-loops"]
}
```

## How to add a new map

1. Create a new folder with the slug name in `maps/` (e.g. `maps/my-map/`)
2. Copy `_template/example.mdx.template` → `<slug>/index.mdx` and `_template/example.meta.json.template` → `<slug>/index.meta.json`
3. Fill in `children` with the slugs/keys of notes this map organizes
4. Write the `.mdx` body -- list all child notes with `[[wiki links]]`
5. Add the slug to `maps/meta.json` `pages` array
6. Run `docker compose up --build` to rebuild and verify

## Closure checklist

A map is **closed** when it has: at least one child, review metadata.
