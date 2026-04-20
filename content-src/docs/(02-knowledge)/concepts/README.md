# concepts/

This folder holds **concept** notes -- atomic ideas and theory.

## Page structure (MDX body)

Every `.mdx` file in this folder must **not** contain YAML frontmatter (no `---` at the top). The body uses `##` headings in this exact order. Omit inapplicable sections but never reorder.

```
## What this is
## Why this matters
## Where this fits
## Core idea
## Equation or formal logic
## Breakdown
### Terms
### What the equation is really doing
## Plain-English explanation
## Worked example
## ASCII diagram
## Why this is used
## Benefits
## Drawbacks and failure modes
## Where I have used it
## Questions this note answers
## Related notes
## Open questions
## Review
```

The `## Where this fits` section must contain `[[wiki links]]` to the parent map, prerequisites, and any systems/methods/projects that use this concept.

## JSON sidecar structure (*.meta.json)

Every `.mdx` file must have a sibling `.meta.json` with the same base name. The materialiser will reject any mismatch.

**Required fields (build will fail without these):**

| Field | Type | Example |
|-------|------|---------|
| `title` | string | `"Cosine Similarity"` |
| `description` | string | `"A similarity measure based on the angle between two vectors."` |
| `id` | string | `"C-IR-0007"` (prefix `C-`, then domain code, then number) |
| `type` | string | `"concept"` (must be exactly this) |

**Mandatory for knowledge graph completeness (closure will warn without these):**

| Field | Rule | Why |
|-------|------|-----|
| `parent_maps` | >= 1 entry | Upward link (U dimension) |
| `prerequisites` + `related_notes` | >= 2 combined | Lateral links (L dimension) |
| `children` | >= 1 entry | Downward link (D dimension) |
| `related_methods` or `related_systems` or `related_projects` | >= 1 total | Applied link (A dimension) |
| `open_questions` | >= 1 entry | Epistemic link (E dimension) |
| `review_cycle` + `last_reviewed` | both set | Maintenance (M dimension) |

**All available connection fields:**

| Field | Links to | Example values |
|-------|----------|----------------|
| `parent_maps` | Map notes | `["MOC_Similarity_Metrics"]` |
| `prerequisites` | Other concepts | `["vectors", "dot_product"]` |
| `children` | Sub-concepts or comparisons | `["cosine_vs_euclidean_vs_dot"]` |
| `related_notes` | Any peer notes | `["vector_similarity"]` |
| `related_methods` | Method notes | `["dense_retrieval"]` |
| `related_systems` | System notes | `["faiss_setup"]` |
| `related_projects` | Project notes | `["my_project"]` |
| `related_experiments` | Experiment notes | `["embedding_benchmark"]` |
| `related_decisions` | Decision notes | `["use_cosine_over_euclidean"]` |
| `related_standards` | Standard notes | `["metadata-schema"]` |
| `superseded_by` | Replacement note | `["improved_similarity"]` |
| `tags` | Tag strings | `["concept/ir", "concept/maths"]` |
| `aliases` | Alternative names | `["cosine score"]` |
| `domain` | Domain string | `"information_retrieval"` |
| `status` | One of: `draft`, `active`, `evergreen`, `archived` | `"active"` |

Values in connection arrays are **wiki-style keys** (underscores, lowercase) that resolve through the `key_to_note` lookup in the knowledge graph. They can also be slugs like `"cosine-similarity"`.

**Libraries:** If this concept relates to a library in the library registry, ask the maintainer to set `docs_tag` on that library entry in `tools/lib-registry/config/libraries.yaml` to point to this note's slug.

## Folder navigation (meta.json)

Each folder must have a `meta.json` that controls sidebar ordering. Sub-domain folders (e.g. `information-retrieval/`) list their child pages:

```json
{
  "title": "Information Retrieval",
  "pages": ["cosine-similarity", "dot-product", "vector-similarity"]
}
```

When you add a new page, **you must also add its slug to the `pages` array** in the parent folder's `meta.json`, otherwise it will not appear in the sidebar.

The top-level `concepts/meta.json` lists the sub-domain folders:

```json
{
  "title": "Concepts",
  "icon": "Sparks",
  "pages": ["mathematics", "statistics", "information-retrieval",
            "representation-learning", "machine-learning", "biomedical"]
}
```

## How to add a new concept

1. Create a new folder with the slug name in the appropriate sub-domain folder (e.g. `information-retrieval/my-concept/`)
2. Copy `_template/example.mdx.template` → `<slug>/index.mdx` and `_template/example.meta.json.template` → `<slug>/index.meta.json`
3. Fill in the `.meta.json` — all required fields and as many connection fields as possible
4. Write the `.mdx` body following the heading order above
5. Add the slug to the sub-domain folder's `meta.json` `pages` array
6. Add `[[wiki links]]` in the body wherever you reference another note
7. Run `docker compose up --build` to rebuild and verify — it will fail if anything is wrong

## Closure checklist

A concept note is **closed** (6/6) when it has:
- One parent map (U)
- Two peers or prerequisites (L)
- One child, example, or comparison (D)
- One method, system, or project link (A)
- At least one open question (E)
- Review cycle and last-reviewed date set (M)

No concept can be promoted to `evergreen` below 5/6 closure.
