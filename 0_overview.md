# Stack Record — Overview

Read this file first. Then `1_implementation.md` for contracts and templates.
Then `2_starter_content.md` for every file an LLM needs to create.

---

## What this repo is

Stack Record is a long-horizon personal knowledge system built on Fumadocs.
Two layers:

1. **Publishing layer** — Fumadocs handles routing, sidebar, slugs, MDX
   rendering, search, and math. It reads from `.generated/docs/` which contains
   standard frontmatter-bearing MDX. This directory is a build artifact.

2. **Knowledge layer** — Stack Record enforces note types, sidecar metadata,
   closure scoring, prerequisites, review loops, and cross-type linking. All
   authored content lives in `content-src/docs/` as body-only `.mdx` paired
   with `.meta.json` sidecars. A build-time materialiser joins them.

**The only custom code in the entire system is the sidecar materialiser**
(`scripts/materialize-fumadocs.ts`). Everything else — routing, page tree,
search, MDX, icons, sidebar — is standard Fumadocs. No custom parsing, no
custom runtime plugins, no custom loaders.

---

## Two-tree architecture

### Authoring tree (`content-src/docs/`) — what you edit

```
content-src/docs/
├── meta.json                    ← Fumadocs folder nav (copied as-is)
├── index.mdx                    ← body only, never has frontmatter
├── index.meta.json              ← page metadata sidecar
├── (01-navigation)/             ← folder group (transparent to URLs)
│   └── maps/
│       ├── meta.json
│       ├── index.mdx + index.meta.json
│       └── learning-map/
│           └── index.mdx + index.meta.json
├── (02-knowledge)/              ← folder group
│   ├── concepts/
│   │   ├── meta.json
│   │   ├── index.mdx + index.meta.json
│   │   └── mathematics/
│   │       ├── meta.json
│   │       └── vectors/
│   │           └── index.mdx + index.meta.json
│   ├── methods/
│   └── systems/
├── (03-operations)/             ← folder group
│   ├── projects/
│   ├── decisions/
│   └── experiments/
├── (04-governance)/             ← folder group
│   ├── standards/
│   └── appendices/
└── (05-inbox)/                  ← folder group
    └── notes/
```

### Generated tree (`.generated/docs/`) — what Fumadocs reads

```
.generated/docs/
├── meta.json                    ← copied verbatim from content-src
├── index.mdx                    ← body + injected frontmatter from sidecar
├── concepts/...
└── ...
```

`.generated/` is gitignored and wiped on every build. Never edit it.

### File type rules

| File pattern | What it is | Materialiser action |
|---|---|---|
| `meta.json` | Fumadocs folder nav (title, icon, pages) | Copied verbatim |
| `*.meta.json` | Page metadata sidecar (knowledge graph) | Merged as frontmatter into matching `.mdx` |
| `*.mdx` | Body content only — **no frontmatter** | Combined with sidecar, written to `.generated/` |

Hard invariants:
- Every `.mdx` must have a matching `.meta.json` (same stem: `index.mdx` ↔ `index.meta.json`)
- Every `.meta.json` must have a matching `.mdx`
- No `.mdx` under `content-src/` may begin with `---`
- The materialiser fails on any violation

---

## Content taxonomy

Nine top-level sections. Each maps to a note type.

| Section | Note type | Purpose |
|---|---|---|
| `concepts/` | `concept` | Atomic ideas and theory |
| `methods/` | `method` | Repeatable procedures |
| `systems/` | `system` | Concrete implementations |
| `decisions/` | `decision` | Architectural decision records |
| `experiments/` | `experiment` | Hypotheses, procedures, results |
| `projects/` | `project` | Project-level synthesis |
| `maps/` | `map` | Navigation and orientation (MOCs) |
| `standards/` | `standard` | Rules for the system itself |
| `appendices/` | `reference` | Templates, glossary, notation |

Sections nest via subfolders (e.g. `concepts/information-retrieval/`,
`systems/compute/`). Every subfolder needs a `meta.json` and typically an
`index.mdx` + `index.meta.json` pair acting as a map note.

All nine sections live inside Fumadocs folder groups for filesystem
organization: `(01-navigation)/maps`, `(02-knowledge)/concepts`,
`(02-knowledge)/methods`, `(02-knowledge)/systems`,
`(03-operations)/projects`, `(03-operations)/decisions`,
`(03-operations)/experiments`, `(04-governance)/standards`,
`(04-governance)/appendices`. The `(05-inbox)/notes` section holds raw
captures. Folder groups are transparent to routing and URLs.

---

## Sidecar metadata schema

Every `.meta.json` carries structured fields. The materialiser passes all
fields through to YAML frontmatter without filtering.

### Required fields (every note)

| Field | Type | Example |
|---|---|---|
| `title` | string | `"Cosine Similarity"` |
| `description` | string | `"Angle-based vector similarity"` |
| `id` | string | `"C-IR-0007"` |
| `type` | enum | `concept`, `method`, `system`, `decision`, `experiment`, `project`, `map`, `standard`, `reference` |
| `status` | enum | `draft`, `active`, `evergreen`, `enforced`, `accepted`, `rejected`, `completed`, `superseded`, `archived` |
| `review_cycle` | enum | `weekly`, `monthly`, `quarterly`, `yearly`, `never` |

### Optional fields (knowledge graph)

`domain`, `tags`, `aliases`, `icon`, `parent_maps`, `prerequisites`,
`children`, `related_notes`, `related_methods`, `related_systems`,
`related_projects`, `last_reviewed`, `closure_score`, `closure_status`,
`open_questions`.

Type-specific fields (e.g. `uses_concepts`, `implemented_in`, `validated_by`,
`date_decided`, `deciders`, `alternatives`, `date_started`,
`date_completed`, `key_methods`, `key_systems`, `key_decisions`) are also
valid. The materialiser passes everything through.

---

## Closure system

Every note is scored across six binary dimensions:

| Dim | Name | Satisfied when |
|---|---|---|
| U | Upward | Links to at least one parent map |
| L | Lateral | Links to at least two peer notes or prerequisites |
| D | Downward | Links to at least one child, example, or comparison |
| A | Applied | Links to at least one project, system, or experiment |
| E | Epistemic | States limitations, failure modes, or open questions |
| M | Maintenance | Has status, review cycle, and last-reviewed date |

Score = U+L+D+A+E+M (0–6). 6/6 = closed. 4–5 = usable. 0–3 = orphan.
No note promoted to `evergreen` below 5/6.

`maps/open-loops.mdx` tracks all notes below threshold.

`lib/closure.ts` implements `scoreClosure()`. `lib/note-types.ts` defines
the TypeScript types.

---

## Materialisation pipeline

```
content-src/docs/**/*.mdx  +  content-src/docs/**/*.meta.json
                    │
                    ▼
    scripts/materialize-fumadocs.ts
    (reads pairs, validates, joins body + sidecar → frontmatter)
                    │
                    ▼
            .generated/docs/**/*.mdx  (with frontmatter)
            .generated/docs/**/meta.json  (copied verbatim)
                    │
                    ▼
        source.config.ts → defineDocs({ dir: '.generated/docs' })
                    │
                    ▼
        .source/ (auto-generated Fumadocs types — gitignored)
                    │
                    ▼
        lib/source.ts → loader() → page tree + icon resolver
                    │
                    ▼
        app/docs/layout.tsx → DocsLayout
                    │
                    ▼
        app/docs/[[...slug]]/page.tsx → renders MDX
```

The materialiser runs before `dev` and `build` via npm scripts:
- `pnpm docs:materialize` → `tsx scripts/materialize-fumadocs.ts`
- `pnpm dev` → `pnpm docs:materialize && next dev`
- `pnpm build` → `pnpm docs:materialize && next build`

### Materialiser hard failures

The script must fail and halt on:
- Missing sidecar for an `.mdx` file
- Orphan `.meta.json` without a matching `.mdx`
- Authored `.mdx` that begins with `---` (frontmatter detected in source)
- Missing required fields (`title`, `description`, `id`, `type`) in sidecar

The materialiser is the **only custom build step**. After it runs, everything
downstream is standard Fumadocs.

---

## The five-layer operating system

This is how the layers fit together at runtime.

### Layer 1 — Visible website

Fumadocs builds the visible site from the generated content tree, page files,
frontmatter, and `meta.json`. Standard Fumadocs page conventions.

### Layer 2 — Invisible knowledge graph

Sidecar fields hold: note type, parent maps, prerequisites, related methods,
related systems, related projects, review rules, and closure fields. These
are injected as frontmatter by the materialiser and are available to any
tooling that reads the generated files.

### Layer 3 — Authoring standard

Each note type uses one rigid template. Section order is fixed per type.
Templates are in `1_implementation.md` section 5 and documented in
`content-src/docs/appendices/templates.mdx`.

### Layer 4 — Quality control

The closure rule scores every note 0–6. Notes below 5/6 cannot be promoted
to `evergreen`. The `open-loops.mdx` page surfaces incomplete notes.

### Layer 5 — Review loop

Any note with low closure or unresolved questions appears in `open-loops.mdx`.
Review cycles (`weekly`, `monthly`, `quarterly`, `yearly`, `never`) drive
when a note is next examined.

---

## Immutable code rules

These apply to all code in the repo and cannot be overridden.

### Central configuration — no scattered defaults

| Scope | Where it lives |
|---|---|
| Theme colours, spacing, fonts | `app/global.css` `@theme` block |
| Icon stroke weights | `lib/source.ts` (`NAV_STROKE`, `TITLE_STROKE`) |
| Site identity (title, nav) | `lib/layout.shared.tsx` `baseOptions()` |
| Content tree + sidebar order | `content-src/docs/**/meta.json` |
| MDX plugins (math, etc.) | `source.config.ts` |
| Next.js config | `next.config.mjs` |
| Knowledge graph types | `lib/note-types.ts` |
| Closure logic | `lib/closure.ts` |
| Materialisation config | `scripts/materialize-fumadocs.ts` (SRC_DIR, OUT_DIR) |

No function parameter defaults. No magic numbers. Every tuneable traces to
this table.

### No inline TypeScript style changes

All styling is CSS-only via `global.css` custom properties. Components never
use inline `style={}` props, hardcoded colour literals, or `className` colour
overrides.

### No frontmatter in authored MDX

Authored `.mdx` files are body-only. All metadata lives in `.meta.json`
sidecars. The materialiser injects frontmatter into `.generated/` output.
No human or LLM ever writes frontmatter into files under `content-src/`.

### Layout and page own the "lib" layer

```
app/             → routing (Next.js App Router)
lib/             → shared logic (source, types, closure, layout config)
components/      → reusable UI (MDX registry, breadcrumb)
scripts/         → build-time tooling (materialiser)
content-src/     → authored content (body + sidecar pairs)
.generated/      → build artifacts (gitignored)
```

### Hyperparameter consolidation

To change how the site **looks** → edit `app/global.css`
To change what content is **shown** → edit `meta.json` files in `content-src/`
To change how content is **processed** → edit `source.config.ts`
To change the **knowledge schema** → edit `lib/note-types.ts`
To change **site identity** → edit `lib/layout.shared.tsx`

### Lean on Fumadocs

No custom routing, no custom page-tree logic, no custom search, no custom
MDX processing. The only custom code is the sidecar materialiser. Everything
else uses Fumadocs' documented APIs exactly as designed.

---

## Technology stack

| Layer | Technology | Version |
|---|---|---|
| Framework | Next.js (App Router) | `^16.x` |
| Docs engine | `fumadocs-core` + `fumadocs-mdx` + `fumadocs-ui` | `latest` |
| Styling | Tailwind CSS v4 | `^4.x` via `@tailwindcss/postcss` |
| Icons | `iconoir-react` | `^7.x` |
| Fonts | Plus Jakarta Sans + JetBrains Mono | Google Fonts (next/font) |
| Math | `remark-math` + `rehype-katex` + `katex` | When activated |
| Materialiser | `gray-matter` (frontmatter serialisation) | `^4.x` |
| Build runner | `tsx` (dev dependency) | `^4.x` |
| Types | TypeScript | `^5.8` |
| Container | Docker + docker-compose | Standalone output |

---

## Note templates (by type)

Each note type has a rigid body template (section order) and a sidecar
template. These are documented in `content-src/docs/appendices/templates.mdx`.
The templates for all nine types are specified in `1_implementation.md`.

The templates enforce:
- Define before explaining
- Stable section order per type
- Plain-English interpretation for technical notes
- At least one worked example
- Drawbacks and failure modes
- Outward links
- Review metadata

---

## Structural principle

- Folders are **stable homes** (navigation)
- Maps are **orientation** (how things connect)
- Sidecars are **structured semantics** (machine-readable graph)
- Body links are **reasoning** (human-readable connections)
- Closure is **quality control** (completeness enforcement)

Folder depth is navigation. The knowledge graph lives in sidecars and links.
Do not let folder depth become the main conceptual hierarchy.

### Max depth rule — four levels

```
Level 1: content-src/docs/                          (root)
Level 2: concepts/ | methods/ | systems/ | ...      (section)
Level 3: mathematics/ | retrieval/ | compute/ | ... (domain)
Level 4: vectors/index.mdx | rrf-pipeline/index.mdx (article)
```

Articles live at Level 4. Domain folders (Level 3) may not contain
sub-domain folders. If a domain grows too large, split it into sibling
domains at Level 3 rather than nesting deeper.

### Folder groups — filesystem organization only

Folder groups (`(01-navigation)/`, `(02-knowledge)/`, etc.) are Fumadocs
route groups: transparent to URLs, invisible in the sidebar. They exist
only for filesystem organization. The `meta.json` extract syntax
(`"...(01-navigation)"`) inlines their contents into the parent page tree.

---

## What not to do

- Never write frontmatter in files under `content-src/`
- Never edit files under `.generated/`
- Never add knowledge-graph metadata to `meta.json` (that's for sidecars)
- Never hardcode colours, sizes, or spacing outside `global.css`
- Never add inline TypeScript styles to components
- Never create parallel config systems
- Never add custom Fumadocs loaders, custom routing, or custom page-tree logic
- Never skip the materialiser in dev or build scripts
- Never promote a note to `evergreen` below 5/6 closure
- Never nest domain folders inside domain folders (max depth = 4)
- Never add numbered prefixes to visible folders (they pollute URLs)
- Never put content directly inside a folder group — content must be inside a section folder within the group
