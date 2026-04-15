# experiments/

This folder holds **experiment** notes -- hypotheses, procedures, and results.

Pages go into sub-folders by status: `active/`, `completed/`, `failed/`.

## Page structure (MDX body)

Every `.mdx` file must **not** contain YAML frontmatter. Use `##` headings in this exact order:

```
## Question
## Hypothesis
## Why this matters
## Setup
## Procedure
## Results
## Interpretation
## Threats to validity
## What this changes
## Final status
```

## JSON sidecar structure (*.meta.json)

**Required fields (build will fail without these):**

| Field | Type | Example |
|-------|------|---------|
| `title` | string | `"Embedding Dimension Benchmark"` |
| `description` | string | `"Testing 768 vs 1024 dim embeddings for biomedical retrieval."` |
| `id` | string | `"E-RET-0001"` (prefix `E-`, then domain code, then number) |
| `type` | string | `"experiment"` (must be exactly this) |

**Mandatory for knowledge graph completeness:**

| Field | Rule | Why |
|-------|------|-----|
| `related_methods` or `related_systems` | >= 1 total | What this tests |
| `related_projects` | >= 1 entry | Which project benefits |
| `date_started` | set | When it began |
| `open_questions` | >= 1 entry | Epistemic link |

**All available connection fields:**

| Field | Links to |
|-------|----------|
| `related_notes` | Any peer notes |
| `related_methods` | Method notes being tested |
| `related_systems` | System notes being tested |
| `related_projects` | Project notes |
| `related_decisions` | Decision notes this informs |
| `blocked_by` | Notes that must be completed first |
| `date_started` | ISO date string |
| `date_completed` | ISO date string (when finished) |
| `tags`, `domain`, `status` | Metadata |

## Folder navigation (meta.json)

Place experiments in the correct status sub-folder. When an experiment finishes, move both files to `completed/` or `failed/` and update both `meta.json` files.

## How to add a new experiment

1. Create a new folder with the slug name in `active/` (e.g. `active/my-experiment/`)
2. Copy `_template/example.mdx.template` → `<slug>/index.mdx` and `_template/example.meta.json.template` → `<slug>/index.meta.json`
3. Fill in all fields -- especially `date_started` and `related_methods`
4. Write the `.mdx` body -- fill in what you can, leave Results/Interpretation empty
5. Add the slug to `active/meta.json` `pages` array
6. Run `docker compose up --build` to rebuild and verify

## Closure checklist

An experiment is **closed** when it has: question, hypothesis, setup, procedure, results, interpretation, threats to validity, feedback links to affected notes.
