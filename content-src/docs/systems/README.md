# systems/

This folder holds **system** notes -- concrete implementations and infrastructure.

## Page structure (MDX body)

Every `.mdx` file must **not** contain YAML frontmatter. Use `##` headings in this exact order:

```
## What this system is
## Why this exists
## Where this fits
## Architecture
## Components
## Configuration contract
## Why it is used
## Benefits
## Drawbacks
## Failure modes
## Monitoring
## Where I have used it
## Related notes
## Open questions
## Review
```

The `## Where this fits` section must contain `[[wiki links]]` to the parent map, methods it implements, and projects.

## JSON sidecar structure (*.meta.json)

**Required fields (build will fail without these):**

| Field | Type | Example |
|-------|------|---------|
| `title` | string | `"RabbitMQ Central Broker"` |
| `description` | string | `"Central queue broker coordinating GPU and CPU consumers."` |
| `id` | string | `"S-CMP-0004"` (prefix `S-`, then domain code, then number) |
| `type` | string | `"system"` (must be exactly this) |

**Mandatory for knowledge graph completeness:**

| Field | Rule | Why |
|-------|------|-----|
| `parent_maps` | >= 1 entry | Upward link (U) |
| `implements_methods` | >= 1 entry | What methods this system realizes |
| `depends_on` | >= 1 entry | Infrastructure dependencies |
| `used_in_projects` | >= 1 entry | Applied link |
| `open_questions` | >= 1 entry | Epistemic link (E) |
| `review_cycle` + `last_reviewed` | both set | Maintenance (M) |

**All available connection fields:**

| Field | Links to |
|-------|----------|
| `parent_maps` | Map notes |
| `implements_methods` | Method notes |
| `depends_on` | Other system notes |
| `used_in_projects` | Project notes |
| `related_notes` | Any peer notes |
| `related_methods` | Method notes |
| `related_systems` | Other system notes |
| `related_projects` | Project notes |
| `related_experiments` | Experiment notes |
| `related_decisions` | Decision notes |
| `tags`, `domain`, `status`, `aliases` | Metadata |

**Libraries:** If this system uses a library from the registry, set `docs_tag` on that library in `tools/lib-registry/config/libraries.yaml` pointing to this note's slug.

## Folder navigation (meta.json)

Sub-folders list their pages. When adding a new system, add its slug to the sub-folder's `meta.json` `pages` array.

## How to add a new system

1. Create a new folder with the slug name in the sub-folder (e.g. `compute/my-system/`)
2. Copy `_template/example.mdx.template` → `<slug>/index.mdx` and `_template/example.meta.json.template` → `<slug>/index.meta.json`
3. Fill in all fields, especially `implements_methods` and `depends_on`
4. Write the `.mdx` body -- include an architecture diagram
5. Add the slug to the sub-folder's `meta.json` `pages` array
6. Run `docker compose up --build` to rebuild and verify

## Closure checklist

A system is **closed** when it has: parent map, implemented method, dependencies, architecture diagram, config contract, failure modes, monitoring, where used, review metadata.
