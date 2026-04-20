# methods/

This folder holds **method** notes -- repeatable procedures and algorithms.

## Page structure (MDX body)

Every `.mdx` file must **not** contain YAML frontmatter. Use `##` headings in this exact order:

```
## What this method is
## Why this is used
## Where this fits
## Inputs
## Outputs
## Procedure
## Formal rule or formula
## Why it works
## Code sketch
## Benefits
## Drawbacks
## Failure modes
## Where I have used it
## Validation and evidence
## Questions this note answers
## Related notes
## Open questions
## Review
```

The `## Where this fits` section must contain `[[wiki links]]` to parent maps, concepts used, systems that implement it, and projects.

## JSON sidecar structure (*.meta.json)

Every `.mdx` must have a sibling `.meta.json` with the same base name.

**Required fields (build will fail without these):**

| Field | Type | Example |
|-------|------|---------|
| `title` | string | `"Reciprocal Rank Fusion Pipeline"` |
| `description` | string | `"A rank-fusion method for combining retrieval systems..."` |
| `id` | string | `"M-RET-0012"` (prefix `M-`, then domain code, then number) |
| `type` | string | `"method"` (must be exactly this) |

**Mandatory for knowledge graph completeness:**

| Field | Rule | Why |
|-------|------|-----|
| `parent_maps` | >= 1 entry | Upward link (U) |
| `uses_concepts` | >= 1 entry | What concepts this method depends on |
| `implemented_in` | >= 1 entry | Which systems implement this |
| `validated_by` | >= 1 entry | How it is tested |
| `related_projects` | >= 1 entry | Applied link (A) |
| `open_questions` | >= 1 entry | Epistemic link (E) |
| `review_cycle` + `last_reviewed` | both set | Maintenance (M) |

**All available connection fields:**

| Field | Links to | Example values |
|-------|----------|----------------|
| `parent_maps` | Map notes | `["Method_Map"]` |
| `uses_concepts` | Concept notes | `["rank_fusion", "score_distributions"]` |
| `implemented_in` | System notes | `["rrf_pipeline"]` |
| `validated_by` | Experiment/system notes | `["two_judge_evaluation"]` |
| `related_notes` | Any peer notes | `["threshold_selection"]` |
| `related_methods` | Other method notes | `[]` |
| `related_systems` | System notes | `["rrf_pipeline"]` |
| `related_projects` | Project notes | `["my_project"]` |
| `related_experiments` | Experiment notes | `[]` |
| `related_decisions` | Decision notes | `[]` |
| `related_standards` | Standard notes | `[]` |
| `tags` | Tag strings | `["method/retrieval"]` |
| `domain` | Domain string | `"retrieval"` |
| `status` | One of: `draft`, `active`, `evergreen`, `archived` | `"active"` |

**Libraries:** If this method is implemented by a library in the registry, set `docs_tag` on that library in `tools/lib-registry/config/libraries.yaml`.

## Folder navigation (meta.json)

Sub-folders (e.g. `retrieval/`) list their pages:

```json
{
  "title": "Retrieval",
  "pages": ["rrf-pipeline"]
}
```

When you add a new method, add its slug to the parent sub-folder's `meta.json` `pages` array.

## How to add a new method

1. Create a new folder with the slug name in the sub-folder (e.g. `retrieval/my-method/`)
2. Copy `_template/example.mdx.template` → `<slug>/index.mdx` and `_template/example.meta.json.template` → `<slug>/index.meta.json`
3. Fill in the `.meta.json`
4. Write the `.mdx` body following the heading order
5. Add the slug to the sub-folder's `meta.json` `pages` array
6. Run `docker compose up --build` to rebuild and verify

## Closure checklist

A method is **closed** when it has: parent map, concept dependencies, implementation link, validation link, inputs/outputs documented, benefits/drawbacks, failure modes, where used, review metadata.
