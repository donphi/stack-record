# Stack Record — Implementation Contracts

Read `0_overview.md` first for architecture. This file covers file-level
contracts, the materialiser spec, all templates, and operational rules.
`2_starter_content.md` has every file's actual contents.

---

## 1. File authority map

### Root config

| File | Purpose | Edit scope |
|---|---|---|
| `package.json` | Deps + scripts (`docs:materialize`, `dev`, `build`, `postinstall`) | Deps and scripts only |
| `next.config.mjs` | Next.js (standalone output, `createMDX()` wrapper) | Build settings only |
| `source.config.ts` | `defineDocs({ dir: '.generated/docs' })` + MDX plugins | Plugins only |
| `tsconfig.json` | TS config + path aliases (`@/*`, `collections/*`) | Aliases only |
| `postcss.config.mjs` | PostCSS (Tailwind v4) | Never change |
| `Dockerfile` / `docker-compose.yml` | Container | Deployment only |
| `.gitignore` | Must include `.generated/`, `.source/`, `.next/`, `node_modules/` | When adding dirs |

### App layer

| File | Rules |
|---|---|
| `app/layout.tsx` | Root shell: fonts, RootProvider, KaTeX CSS. No styles, no logic. |
| `app/global.css` | **All visual config.** Single source for CSS custom properties. |
| `app/docs/layout.tsx` | `DocsLayout` + page tree. No custom logic. |
| `app/docs/[[...slug]]/page.tsx` | Renders MDX via Fumadocs. No custom data fetching. |
| `app/(home)/layout.tsx` | Minimal wrapper. |
| `app/(home)/page.tsx` | Landing content only. |
| `app/api/search/route.ts` | `createFromSource(source)`. No custom logic. |

### Lib layer

| File | Exports |
|---|---|
| `lib/source.ts` | `source` (Fumadocs loader), `getPageIcon()`, `NAV_STROKE`, `TITLE_STROKE` |
| `lib/layout.shared.tsx` | `baseOptions()` — site title, nav |
| `lib/note-types.ts` | `NoteType`, `ClosureStatus`, `ReviewCycle`, `BaseNoteMeta` |
| `lib/closure.ts` | `scoreClosure(meta)` → `ClosureBreakdown` |

### Components

| File | Purpose |
|---|---|
| `components/mdx.tsx` | MDX component registry (Steps, default components) |
| `components/breadcrumb.tsx` | Custom breadcrumb from page tree |

### Scripts

| File | Purpose |
|---|---|
| `scripts/materialize-fumadocs.ts` | Joins `content-src/` body + sidecar → `.generated/` |

---

## 2. Materialiser contract

The **only custom code** in the build pipeline.

### I/O

- Input: `content-src/docs/` (SRC_DIR)
- Output: `.generated/docs/` (OUT_DIR) — wiped and regenerated every run

### Steps

1. Recursively list all files in SRC_DIR
2. Classify: `.mdx`/`.md` = body, `meta.json` = folder meta, `*.meta.json` = page sidecar
3. Validate pairing (every body ↔ sidecar), reject frontmatter in bodies
4. Validate required sidecar fields: `title`, `description`, `id`, `type`
5. Copy folder `meta.json` files verbatim
6. For each body: read body + sidecar, serialize sidecar as YAML frontmatter via `gray-matter`, write to OUT_DIR
7. Log count and exit

### Hard failures

| Condition | Error message |
|---|---|
| `.mdx` without `.meta.json` | `Missing sidecar meta file for page body` |
| `.meta.json` without `.mdx` | `Orphan page meta file without matching body` |
| `.mdx` starts with `---` | `Authored body file must not contain frontmatter` |
| Missing required field | `Missing required "field" in path` |

### Dependencies

- `gray-matter` (runtime) — frontmatter serialisation
- `tsx` (devDependency) — TypeScript script runner

---

## 3. Package.json scripts

```json
{
  "docs:materialize": "tsx scripts/materialize-fumadocs.ts",
  "dev": "pnpm docs:materialize && next dev",
  "build": "pnpm docs:materialize && next build",
  "start": "next start",
  "postinstall": "fumadocs-mdx"
}
```

---

## 4. Sidecar templates (JSON)

### Concept

```json
{
  "title": "", "description": "", "id": "C-{{CODE}}", "type": "concept",
  "domain": "", "status": "evergreen", "tags": ["concept/{{TAG}}"],
  "aliases": [], "icon": "",
  "parent_maps": [], "prerequisites": [], "children": [],
  "related_notes": [], "related_methods": [], "related_systems": [], "related_projects": [],
  "review_cycle": "monthly", "last_reviewed": "",
  "closure_score": 0, "closure_status": "open", "open_questions": []
}
```

### Method

```json
{
  "title": "", "description": "", "id": "M-{{CODE}}", "type": "method",
  "domain": "", "status": "evergreen", "tags": ["method/{{TAG}}"],
  "icon": "",
  "parent_maps": [], "uses_concepts": [], "implemented_in": [], "validated_by": [],
  "related_notes": [], "related_methods": [], "related_systems": [], "related_projects": [],
  "review_cycle": "monthly", "last_reviewed": "",
  "closure_score": 0, "closure_status": "open", "open_questions": []
}
```

### System

```json
{
  "title": "", "description": "", "id": "S-{{CODE}}", "type": "system",
  "domain": "", "status": "active", "tags": ["system/{{TAG}}"],
  "icon": "",
  "parent_maps": [], "implements_methods": [], "depends_on": [], "used_in_projects": [],
  "related_notes": [], "related_methods": [], "related_systems": [], "related_projects": [],
  "review_cycle": "quarterly", "last_reviewed": "",
  "closure_score": 0, "closure_status": "open", "open_questions": []
}
```

### Decision

```json
{
  "title": "", "description": "", "id": "D-{{CODE}}", "type": "decision",
  "domain": "", "status": "accepted", "tags": ["decision/{{TAG}}"],
  "decision_status": "accepted", "date_decided": "", "deciders": ["Your Name"],
  "alternatives": [], "related_projects": [],
  "review_cycle": "yearly", "last_reviewed": "",
  "closure_score": 0, "closure_status": "open", "open_questions": []
}
```

### Experiment

```json
{
  "title": "", "description": "", "id": "E-{{CODE}}", "type": "experiment",
  "domain": "", "status": "completed", "tags": ["experiment/{{TAG}}"],
  "related_notes": [], "related_methods": [], "related_systems": [], "related_projects": [],
  "date_started": "", "date_completed": "",
  "review_cycle": "never", "last_reviewed": "",
  "closure_score": 0, "closure_status": "open", "open_questions": []
}
```

### Project

```json
{
  "title": "", "description": "", "id": "P-{{CODE}}", "type": "project",
  "domain": "project", "status": "active", "tags": ["project/{{TAG}}"],
  "related_notes": [], "related_methods": [], "related_systems": [], "related_projects": [],
  "key_methods": [], "key_systems": [], "key_decisions": [],
  "review_cycle": "monthly", "last_reviewed": "",
  "closure_score": 0, "closure_status": "open", "open_questions": []
}
```

### Map

```json
{
  "title": "", "description": "", "id": "MAP-{{CODE}}", "type": "map",
  "domain": "", "status": "evergreen", "tags": ["map/{{TAG}}"],
  "children": [],
  "review_cycle": "quarterly", "last_reviewed": "",
  "closure_score": 0, "closure_status": "open", "open_questions": []
}
```

### Standard

```json
{
  "title": "", "description": "", "id": "STD-{{CODE}}", "type": "standard",
  "domain": "standards", "status": "enforced", "tags": ["standard/{{TAG}}"],
  "review_cycle": "yearly", "last_reviewed": "",
  "closure_score": 6, "closure_status": "closed", "open_questions": []
}
```

### Reference

```json
{
  "title": "", "description": "", "id": "REF-{{CODE}}", "type": "reference",
  "domain": "", "status": "evergreen", "tags": ["reference/{{TAG}}"],
  "review_cycle": "yearly", "last_reviewed": "",
  "closure_score": 6, "closure_status": "closed", "open_questions": []
}
```

---

## 5. Body templates (MDX section order)

No frontmatter. Omit inapplicable sections but preserve order.

### Concept

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

### Method

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

### System

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

### Decision

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

### Experiment

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

### Project

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

### Map

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

### Standard

```
## Purpose
## Applies to
## Required fields
## Required sections
## Quality bar
## Failure conditions
```

---

## 6. Content tree structure

```
content-src/docs/
├── meta.json + index.mdx + index.meta.json
├── (01-navigation)/
│   └── maps/              (meta.json + index pair + article folders: learning-map/, domain-map/,
│                           method-map/, system-map/, open-loops/)
├── (02-knowledge)/
│   ├── concepts/          (meta.json + index pair + subfolders: mathematics, statistics,
│   │                       information-retrieval, representation-learning, machine-learning, biomedical)
│   │                       Each leaf article is a folder: slug/index.mdx + slug/index.meta.json
│   ├── methods/           (meta.json + index pair + subfolders: extraction, retrieval,
│   │                       evaluation, reproducibility, build)
│   └── systems/           (meta.json + index pair + subfolders: pipeline, data, compute,
│                           runtime, security)
├── (03-operations)/
│   ├── projects/          (meta.json + index pair + subfolders: your-project-name)
│   ├── decisions/         (meta.json + index pair + subfolders: accepted, rejected, pending)
│   └── experiments/       (meta.json + index pair + subfolders: active, completed, failed)
├── (04-governance)/
│   ├── standards/         (meta.json + index pair + article folders: closure-rule/, metadata-schema/,
│   │                       writing-style/, note-quality-bar/)
│   └── appendices/        (meta.json + article folders: glossary/, notation/, templates/)
└── (05-inbox)/
    └── notes/             (meta.json + index pair + inbox notes)
```

---

## 7. Hyperparameter hierarchy

When changing a setting, check this order. Change it at the right level.

| Level | File | Controls |
|---|---|---|
| 1 | `app/global.css` | All colours, sizes, spacing, dark mode, sidebar styles |
| 2 | `lib/source.ts` | `NAV_STROKE`, `TITLE_STROKE` (icon weights, React props not CSS) |
| 3 | `lib/layout.shared.tsx` | Site title, nav config |
| 4 | `source.config.ts` | Content dir, MDX plugins |
| 5 | `next.config.mjs` | Standalone output, Next.js-level settings |

---

## 8. Writing standards

1. Define before explaining
2. Stable section order per note type
3. Plain-English interpretation for technical notes
4. One worked example minimum
5. Show drawbacks — no note only sells the idea
6. Link outward to related notes and usage
7. Write for decision utility — reader leaves knowing what to do

**Math notes additionally:** equation, breakdown, variable defs, interpretation, example.
**System notes additionally:** architecture diagram, config contract, failure modes, monitoring.
**Decision notes additionally:** alternatives, tradeoffs, consequences, review trigger.

---

## 9. Closure checklists

### Concept: closed when it has
one parent map, two peers/prerequisites, one child/example, one method link,
one system/project link, drawbacks, open questions, review metadata

### Method: closed when it has
one parent map, concept dependencies, implementation link, validation link,
inputs/outputs, benefits/drawbacks, failure modes, where used, review metadata

### System: closed when it has
one parent map, implemented method, dependencies, architecture diagram,
config contract, failure modes, monitoring, where used, review metadata

### Decision: closed when it has
context, options, why chosen, tradeoffs, consequences, review trigger

### Experiment: closed when it has
question, hypothesis, setup, procedure, results, interpretation,
threats to validity, feedback links

---

## 10. Build order for initial setup

1. `scripts/materialize-fumadocs.ts`
2. `lib/note-types.ts` + `lib/closure.ts`
3. `source.config.ts` (point at `.generated/docs`)
4. `lib/source.ts`
5. Root `content-src/docs/meta.json`
6. Standards section (closure-rule, metadata-schema, writing-style, note-quality-bar)
7. One concept pair (e.g. cosine-similarity)
8. One method pair (e.g. rrf-pipeline)
9. One system pair (e.g. rabbitmq-central-broker)
10. Maps section (especially open-loops)
11. `app/api/search/route.ts`

---

## 11. What not to do

- Write frontmatter in files under `content-src/`
- Edit files under `.generated/`
- Put knowledge-graph fields in folder `meta.json`
- Hardcode colours/sizes outside `global.css`
- Add inline TypeScript styles
- Add custom Fumadocs loaders, custom routing, or custom page-tree logic
- Skip the materialiser in dev or build
- Promote a note to `evergreen` below 5/6 closure
- Nest domain folders inside domain folders (max depth = 4 levels)
- Add numbered prefixes to visible folders (they pollute URLs; only use on folder groups)
- Put content directly inside a folder group — content must be inside section folders