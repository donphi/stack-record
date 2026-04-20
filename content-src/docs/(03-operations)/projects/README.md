# projects/

This folder holds **project** notes -- synthesis pages that tie together concepts, methods, systems, and decisions.

Each project gets its own sub-folder (e.g. `my-project/`).

## Page structure (MDX body)

Every `.mdx` file must **not** contain YAML frontmatter. Use `##` headings in this exact order:

```
## What this project is
## Why it exists
## Scope
## Key concepts
## Key methods
## Key systems
## Key decisions
## Status
## Lessons learned
## Open loops
```

The `## Key *` sections must use `[[wiki links]]` to connect to the actual concept, method, system, and decision notes.

## JSON sidecar structure (*.meta.json)

**Required fields (build will fail without these):**

| Field | Type | Example |
|-------|------|---------|
| `title` | string | `"My Research Pipeline"` |
| `description` | string | `"End-to-end pipeline for data extraction and processing."` |
| `id` | string | `"P-PROJ-0001"` (prefix `P-`, then code, then number) |
| `type` | string | `"project"` (must be exactly this) |

**Mandatory for knowledge graph completeness:**

| Field | Rule | Why |
|-------|------|-----|
| `key_methods` | >= 1 entry | Core methods used |
| `key_systems` | >= 1 entry | Core systems used |
| `related_notes` | >= 1 entry | Concept links |
| `open_questions` | >= 1 entry | Epistemic link |
| `review_cycle` + `last_reviewed` | both set | Maintenance |

**All available connection fields:**

| Field | Links to |
|-------|----------|
| `key_methods` | Method notes |
| `key_systems` | System notes |
| `key_decisions` | Decision notes |
| `related_notes` | Any notes (concepts, etc.) |
| `related_methods` | Method notes |
| `related_systems` | System notes |
| `related_projects` | Other project notes |
| `related_experiments` | Experiment notes |
| `blocked_by` | Notes blocking progress |
| `tags`, `domain`, `status` | Metadata |

## Folder navigation (meta.json)

Each project sub-folder has its own `meta.json`. New pages within the project go in its `pages` array. New projects must be added to `projects/meta.json`.

## How to add a new project

1. Create a new sub-folder with the project slug
2. Add a `meta.json` with `{"title": "My Project"}`
3. Copy `_template/example.mdx.template` and `_template/example.meta.json.template` into the sub-folder as `index.mdx` / `index.meta.json`
   Remove the `.template` suffix from both files after copying.
4. Fill in all fields
5. Add the sub-folder name to `projects/meta.json` `pages` array
6. Run `docker compose up --build` to rebuild and verify

## Closure checklist

A project is **closed** when it has: key methods, key systems, related concept notes, open questions, review metadata.
