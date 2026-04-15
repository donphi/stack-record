# decisions/

This folder holds **decision** notes (ADRs) -- records of choices made and why.

Pages go into sub-folders by status: `accepted/`, `rejected/`, `pending/`.

## Page structure (MDX body)

Every `.mdx` file must **not** contain YAML frontmatter. Use `##` headings in this exact order:

```
## Decision
## Context
## Why this decision exists
## Options considered
## Why the chosen option won
## Tradeoffs accepted
## Consequences
## Where this has been used
## Review trigger
```

## JSON sidecar structure (*.meta.json)

**Required fields (build will fail without these):**

| Field | Type | Example |
|-------|------|---------|
| `title` | string | `"Use Fumadocs as Publishing Layer"` |
| `description` | string | `"ADR for choosing Fumadocs over custom SSG."` |
| `id` | string | `"D-PUB-0001"` (prefix `D-`, then domain code, then number) |
| `type` | string | `"decision"` (must be exactly this) |

**Mandatory for knowledge graph completeness:**

| Field | Rule | Why |
|-------|------|-----|
| `related_projects` | >= 1 entry | Which project this decision affects |
| `alternatives` | >= 1 entry | What was considered |
| `deciders` | >= 1 entry | Who made the call |
| `date_decided` | set | When it was made |
| `decision_status` | set | `"accepted"`, `"rejected"`, or `"pending"` |
| `open_questions` | >= 1 entry | Epistemic link |

**All available connection fields:**

| Field | Links to |
|-------|----------|
| `related_projects` | Project notes |
| `alternatives` | String list of options considered |
| `deciders` | String list of people |
| `related_notes` | Any peer notes |
| `related_methods` | Method notes |
| `related_systems` | System notes |
| `related_experiments` | Experiment notes |
| `superseded_by` / `supersedes` | Other decision notes |
| `tags`, `domain`, `status` | Metadata |

## Folder navigation (meta.json)

Place decisions in the correct status sub-folder. Each sub-folder's `meta.json` lists its pages. When adding a new decision, add its slug to the sub-folder's `pages` array.

If a decision changes status (e.g. pending -> accepted), move both files to the new sub-folder and update both `meta.json` files.

## How to add a new decision

1. Create a new folder with the slug name in the status sub-folder (e.g. `accepted/my-decision/`)
2. Copy `_template/example.mdx.template` → `<slug>/index.mdx` and `_template/example.meta.json.template` → `<slug>/index.meta.json`
3. Fill in all fields -- especially `alternatives` and `deciders`
4. Write the `.mdx` body following the heading order
5. Add the slug to the sub-folder's `meta.json` `pages` array
6. Run `docker compose up --build` to rebuild and verify

## Closure checklist

A decision is **closed** when it has: context, options considered, why chosen, tradeoffs, consequences, review trigger.
