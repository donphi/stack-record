---
name: Stack Record Sidecar Architecture
overview: Transform the existing Fumadocs repo from a flat content/docs/ structure into the two-tree sidecar architecture (content-src/ + .generated/) described in the three spec files. This involves creating the materialiser script, new lib modules, restructuring all content as body+sidecar pairs, updating configs and scripts, adding rich MDX component templates, and preserving all existing colors/fonts/styling.
todos:
  - id: phase0-deps
    content: "Phase 0: Install new dependencies (gray-matter, remark-math, rehype-katex, katex, tsx) FIRST so imports resolve"
    status: pending
  - id: phase1-tooling
    content: "Phase 1: Create materialize script, lib/note-types.ts, lib/closure.ts, update package.json scripts, source.config.ts, .gitignore"
    status: pending
  - id: phase2-mdx
    content: "Phase 2: Enrich components/mdx.tsx with Tabs, Accordion, Files, TypeTable, ImageZoom; add KaTeX CSS to app/layout.tsx"
    status: pending
  - id: phase3-delete
    content: "Phase 3a: Delete the entire content/docs/ directory"
    status: pending
  - id: phase3-meta
    content: "Phase 3b: Create ALL folder meta.json files in content-src/docs/ (including every stub subfolder)"
    status: pending
  - id: phase3-indexes
    content: "Phase 3c: Create all index.mdx + index.meta.json pairs for every section and subfolder"
    status: pending
  - id: phase3-content
    content: "Phase 3d: Create all example content pages verbatim (concepts, methods, systems, maps, projects)"
    status: pending
  - id: phase3-standards
    content: "Phase 3e: Create all 4 standards pages including closure-rule FULL body from section 10"
    status: pending
  - id: phase4-templates
    content: "Phase 4: Create rich appendices/templates.mdx with all 9 note type templates (body + sidecar + closure checklist) using Fumadocs MDX artifacts; also glossary + notation stubs"
    status: pending
  - id: phase5-docstrings
    content: "Phase 5: Add file-header docstrings (PURPOSE / OWNS / TOUCH POINTS) to every existing and new .ts/.tsx/.css/.mjs file"
    status: pending
  - id: phase6-landing
    content: "Phase 6: Update landing page copy"
    status: pending
  - id: phase7-verify
    content: "Phase 7: Run materialiser, verify no authored .mdx has frontmatter, verify build, audit all headers"
    status: pending
isProject: false
---

# Stack Record Sidecar Architecture Implementation

## Immutable code principles (from 0_overview.md -- MUST GOVERN ALL IMPLEMENTATION)

These rules are non-negotiable and apply to every line of code and content.

- **The only custom code is the materialiser.** No custom routing, no custom page-tree logic, no custom search, no custom MDX processing, no custom loaders. Everything else is standard Fumadocs.
- **Central configuration, no scattered defaults.** Every tuneable traces to exactly one authority file (see table below). No function parameter defaults. No magic numbers.


| Scope                         | Authority file                                       |
| ----------------------------- | ---------------------------------------------------- |
| Theme colours, spacing, fonts | `app/global.css` `@theme` block                      |
| Icon stroke weights           | `lib/source.ts` (NAV_STROKE, TITLE_STROKE)           |
| Site identity (title, nav)    | `lib/layout.shared.tsx` baseOptions()                |
| Content tree + sidebar order  | `content-src/docs/**/meta.json`                      |
| MDX plugins (math, etc.)      | `source.config.ts`                                   |
| Next.js config                | `next.config.mjs`                                    |
| Knowledge graph types         | `lib/note-types.ts`                                  |
| Closure logic                 | `lib/closure.ts`                                     |
| Materialisation config        | `scripts/materialize-fumadocs.ts` (SRC_DIR, OUT_DIR) |


- **No inline TypeScript style changes.** All styling is CSS-only via `global.css` custom properties. Components never use inline `style={}` props with hardcoded colour literals or `className` colour overrides. (The existing `breadcrumb.tsx` references CSS custom properties via `style={}` -- this is acceptable since it reads from `global.css` vars.)
- **No frontmatter in authored MDX.** Every `.mdx` under `content-src/` is body-only. All metadata in `.meta.json` sidecars. The materialiser injects frontmatter into `.generated/`. No human or LLM ever writes `---` at the top of files under `content-src/`.
- **Fixed directory layout.** `app/` = routing, `lib/` = shared logic, `components/` = reusable UI, `scripts/` = build tooling, `content-src/` = authored content, `.generated/` = build artifacts (gitignored).
- **Hyperparameter consolidation.** Looks = `global.css`. Content shown = `meta.json`. Processing = `source.config.ts`. Schema = `lib/note-types.ts`. Identity = `lib/layout.shared.tsx`.
- **Lean on Fumadocs.** Use Fumadocs documented APIs exactly as designed. No wrappers, no abstractions, no middleware.
- **Every file must have a file-header docstring.** See "File header documentation standard" below.

---

## File header documentation standard

Every TypeScript/TSX file in the repo must have a structured header comment at the top (after imports) that makes the file instantly findable and understandable. This is critical for navigating and changing files confidently.

### Format for `.ts` / `.tsx` files

Every file gets a block comment immediately after the import section with exactly three parts:

1. **PURPOSE** -- one sentence: what this file does
2. **OWNS** -- what configuration, logic, or UI this file is the single authority for
3. **TOUCH POINTS** -- which other files read from or depend on this file

Example (for `lib/source.ts`, which already has partial docs):
```ts
/**
 * Fumadocs content loader and icon resolver.
 *
 * OWNS:
 *   - NAV_STROKE (sidebar icon stroke weight — React prop, not CSS)
 *   - TITLE_STROKE (page-title icon stroke weight — React prop, not CSS)
 *   - source (Fumadocs loader instance, baseUrl: /docs)
 *   - getPageIcon() (title icon lookup by URL)
 *
 * TOUCH POINTS:
 *   - app/docs/layout.tsx reads source.getPageTree()
 *   - app/docs/[[...slug]]/page.tsx reads source.getPage(), getPageIcon()
 *   - app/api/search/route.ts reads source
 *   - Icon sizes (CSS) live in app/global.css (--size-nav-icon, --size-title-icon)
 */
```

### Format for `.css` files

`app/global.css` already has good section-divider comments. Ensure each section header references the related code file (e.g., "Stroke weight is set in lib/source.ts"). Add a file-level header at the top:
```css
/*
 * Stack Record — global visual configuration.
 *
 * OWNS: All colours, spacing, fonts, dark mode, sidebar styles,
 *       steps component styling, page-title icon sizing, breadcrumb sizing.
 *
 * RULE: This is the ONLY file for visual tuning.
 *       No inline styles, no hardcoded colours in components.
 *       See 0_overview.md "Immutable code rules" for the full constraint.
 */
```

### Required headers for every file in the repo

| File | PURPOSE line |
|------|-------------|
| `app/layout.tsx` | Root HTML shell: fonts (next/font), RootProvider, KaTeX CSS. |
| `app/global.css` | All visual configuration. Single source for CSS custom properties. |
| `app/docs/layout.tsx` | Docs shell: DocsLayout + page tree. No custom logic. |
| `app/docs/[[...slug]]/page.tsx` | Docs page renderer: MDX body, breadcrumb, title icon, metadata. |
| `app/(home)/layout.tsx` | Landing page shell: HomeLayout with shared nav options. |
| `app/(home)/page.tsx` | Landing page content. |
| `app/api/search/route.ts` | Fumadocs search endpoint. No custom logic. |
| `lib/source.ts` | Fumadocs content loader and icon resolver. |
| `lib/layout.shared.tsx` | Shared layout options: site title, nav config. |
| `lib/note-types.ts` | Knowledge graph type definitions: NoteType, ClosureStatus, ReviewCycle, BaseNoteMeta. |
| `lib/closure.ts` | Closure scoring logic: 6-dimension U-L-D-A-E-M scoring. |
| `components/mdx.tsx` | MDX component registry: maps Fumadocs + custom components for use in .mdx files. |
| `components/breadcrumb.tsx` | Custom breadcrumb navigation from page tree. |
| `scripts/materialize-fumadocs.ts` | Sidecar materialiser: joins content-src/ body + .meta.json into .generated/ with frontmatter. |
| `source.config.ts` | Fumadocs MDX config: content directory, remark/rehype plugins. |
| `next.config.mjs` | Next.js config: standalone output, createMDX wrapper. |

### Rules

- Headers go **after imports, before any code**. For CSS, the header goes at the very top before `@import`.
- The OWNS section lists what this file is the **single authority** for -- so someone searching "where do I change X?" can find it.
- The TOUCH POINTS section lists **which files depend on this file's exports** -- so someone modifying this file knows what might break.
- Do NOT add redundant line-by-line comments. The header replaces the need for narration. Function-level JSDoc is only needed where intent is non-obvious (like the existing `getPageIcon()` doc in `lib/source.ts`).
- Existing files that are "preserved as-is" still get their header added -- this is a documentation change, not a logic change.

---

## What changes and what stays

**Preserved as-is (logic unchanged, file-header docstrings added):**

- [app/global.css](app/global.css) -- all colors, fonts, spacing, sidebar styles, steps styling, dark mode. Add file-level header; existing section comments already good.
- [app/docs/[[...slug]]/page.tsx](app/docs/[[...slug]]/page.tsx) -- MDX rendering, breadcrumb, page icon. Add file header.
- [app/docs/layout.tsx](app/docs/layout.tsx) -- DocsLayout + page tree. Add file header.
- [app/(home)/layout.tsx](app/(home)/layout.tsx) -- HomeLayout wrapper. Add file header.
- [app/(home)/page.tsx](app/(home)/page.tsx) -- Landing page (content updated, header added).
- [lib/source.ts](lib/source.ts) -- icon resolver, NAV_STROKE, TITLE_STROKE. Upgrade existing partial docs to full header format.
- [lib/layout.shared.tsx](lib/layout.shared.tsx) -- baseOptions(), site title. Add file header.
- [components/breadcrumb.tsx](components/breadcrumb.tsx) -- custom breadcrumb. Add file header.
- [next.config.mjs](next.config.mjs) -- createMDX wrapper, standalone output. Add file header.
- [tsconfig.json](tsconfig.json) -- paths, compiler options. No header (JSON).
- [postcss.config.mjs](postcss.config.mjs) -- **never change** (per spec). Add file header.
- [Dockerfile](Dockerfile) -- updated for sidecar architecture (pnpm, materialiser step, content-src paths). Add file header.
- [docker-compose.yml](docker-compose.yml) -- updated (service name fix). Add file header.
- [.dockerignore](.dockerignore) -- updated (content-src instead of content, add .generated).
- [app/api/search/route.ts](app/api/search/route.ts) -- createFromSource, no custom logic. Add file header.

**Deleted entirely:** `content/docs/` directory (all old flat MDX content).

**Created from scratch:**

- `scripts/materialize-fumadocs.ts` -- the only custom code
- `lib/note-types.ts` -- knowledge graph types
- `lib/closure.ts` -- closure scoring
- `content-src/docs/` -- the entire authoring tree (~130 files)

**Modified (minimal, targeted changes only):**

- [package.json](package.json) -- add deps + scripts
- [source.config.ts](source.config.ts) -- point at `.generated/docs`, add math plugins, destructure `{ docs, meta }`
- [.gitignore](.gitignore) -- add `.generated/`
- [components/mdx.tsx](components/mdx.tsx) -- register additional Fumadocs UI components
- [app/layout.tsx](app/layout.tsx) -- add KaTeX CSS import (one line)
- [app/(home)/page.tsx](app/(home)/page.tsx) -- update landing copy
- [Dockerfile](Dockerfile) -- pnpm, materialiser chain, content-src paths
- [docker-compose.yml](docker-compose.yml) -- fix service name
- [.dockerignore](.dockerignore) -- content-src instead of content, add .generated

---

## Phase 0 -- Add dependencies to package.json (Docker-only workflow)

**CRITICAL: This repo runs entirely in Docker. Nothing is installed locally.** Dependencies are added to `package.json` and installed inside the Docker build. No `pnpm install` or `npm install` runs on the host.

Add to `package.json`:
- **dependencies:** `gray-matter`, `remark-math`, `rehype-katex`, `katex`
- **devDependencies:** `tsx`

### 0.1 Update Dockerfile for sidecar architecture

The current Dockerfile uses `npm install` and `npm run build`. It must be updated for:
1. **Use pnpm** (consistent with `pnpm docs:materialize` in scripts) -- install corepack + pnpm in the base stage
2. **Copy `content-src/` and `scripts/`** into the builder stage (needed for materialisation)
3. **The `npm run build` already chains materialiser** via `package.json` scripts (`"build": "pnpm docs:materialize && next build"`) so no separate materialiser step is needed in Dockerfile -- just ensure pnpm is available
4. **Copy pnpm lockfile** instead of npm lockfile in deps stage

Updated Dockerfile structure:
```dockerfile
FROM node:24-alpine AS base
RUN corepack enable && corepack prepare pnpm@latest --activate

FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
COPY source.config.ts next.config.mjs ./
RUN pnpm install --frozen-lockfile || pnpm install

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm run build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
```

### 0.2 Update `.dockerignore`

Current `.dockerignore` references `content/` which no longer exists. Update:
```
node_modules
.next
.generated
.git
*.md
!content-src/**/*.md
!content-src/**/*.mdx
```

### 0.3 Update `docker-compose.yml`

Fix service name (currently `Stack Record` with a space, which is invalid). Update to:
```yaml
services:
  stack-record:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
```

### 0.4 Development workflow

For local development, use Docker Compose or run the container. The `pnpm dev` script inside the container chains `pnpm docs:materialize && next dev`. No host-level node_modules needed.

---

## Phase 1 -- Build tooling and config

### 1.1 Create `scripts/materialize-fumadocs.ts`

Verbatim from `2_starter_content.md` section 1. This is the **only custom code** in the entire system. It:

- Reads from `content-src/docs/` (SRC_DIR)
- Writes to `.generated/docs/` (OUT_DIR), wiped every run
- Copies `meta.json` files verbatim
- For each `.mdx`: validates pairing with `.meta.json`, validates no frontmatter in body, validates required fields (`title`, `description`, `id`, `type`), serialises sidecar as YAML frontmatter via `gray-matter`, writes combined file
- Hard fails on: missing sidecar, orphan sidecar, frontmatter in body, missing required fields (exact error messages from `1_implementation.md` section 2)

### 1.2 Create `lib/note-types.ts`

Exports: `NoteType` (9 values: map, concept, method, system, decision, experiment, project, standard, reference), `ClosureStatus` (4 values: open, partial, closed, archived), `ReviewCycle` (5 values: weekly, monthly, quarterly, yearly, never), `BaseNoteMeta` interface with all required + optional fields. Verbatim from spec.

### 1.3 Create `lib/closure.ts`

Exports: `ClosureBreakdown` interface (6 dimensions each 0|1 + total), `scoreClosure(meta)` function implementing U-L-D-A-E-M scoring. Verbatim from spec.

### 1.4 Update `package.json` scripts

Replace/add exactly these scripts (per `1_implementation.md` section 3):

```json
"docs:materialize": "tsx scripts/materialize-fumadocs.ts",
"dev": "pnpm docs:materialize && next dev",
"build": "pnpm docs:materialize && next build",
"start": "next start",
"postinstall": "fumadocs-mdx"
```

### 1.5 Update `source.config.ts`

Replace entirely with the version from `2_starter_content.md` section 2:

- `import { defineDocs, defineConfig } from 'fumadocs-mdx/config'`
- `import remarkMath from 'remark-math'`
- `import rehypeKatex from 'rehype-katex'`
- `export const { docs, meta } = defineDocs({ dir: '.generated/docs' })`
- `export default defineConfig({ mdxOptions: { remarkPlugins: [remarkMath], rehypePlugins: (v) => [rehypeKatex, ...v] } })`

### 1.6 Update `.gitignore`

Add `.generated/` line. Verify existing entries include: `node_modules/`, `.next/`, `.source/`.

---

## Phase 2 -- Enrich MDX component registry

### 2.1 Update `components/mdx.tsx`

Register additional Fumadocs UI components so all templates can use them without per-file imports:

- `Tab`, `Tabs` from `fumadocs-ui/components/tabs`
- `Accordion`, `Accordions` from `fumadocs-ui/components/accordion`
- `File`, `Folder`, `Files` from `fumadocs-ui/components/files`
- `TypeTable` from `fumadocs-ui/components/type-table`
- `ImageZoom` from `fumadocs-ui/components/image-zoom`

Note: `Callout`, `Card`, `Cards` are already in `defaultMdxComponents`. `Step`, `Steps` are already registered. Make sure they are all correctly linked  to the colors globally, remember NO INLINE CODE ANYTHING. UNLESS it needs to be

### 2.2 Update `app/layout.tsx`

Add one import line for KaTeX CSS per [Fumadocs Math docs](https://fumadocs.dev/docs/markdown/math) and `1_implementation.md` section 1 ("Root shell: fonts, RootProvider, KaTeX CSS"):

```tsx
import 'katex/dist/katex.css';
```

No other changes to this file. Fonts (`next/font` in root layout) and RootProvider are already set up per Fumadocs best practice. Body class stays as-is.

---

## Phase 3 -- Content tree (content-src/docs/)

### 3.0 Delete `content/docs/` entirely

Remove the old flat content directory. It is replaced by the two-tree architecture.

### 3.1 Root and ALL folder meta.json files

Every folder needs a `meta.json` controlling sidebar order. Specified in `2_starter_content.md` section 3 plus `1_implementation.md` section 6 tree:

**Specified verbatim (13 files):**

- `content-src/docs/meta.json` (root: pages include index, maps, concepts, methods, systems, projects, decisions, experiments, standards, appendices)
- `content-src/docs/concepts/meta.json` (defaultOpen: true, pages: index + 6 subfolders)
- `content-src/docs/concepts/information-retrieval/meta.json`
- `content-src/docs/methods/meta.json` (pages: index, extraction, retrieval, evaluation, reproducibility, build)
- `content-src/docs/methods/retrieval/meta.json`
- `content-src/docs/systems/meta.json` (pages: index, pipeline, data, compute, runtime, security)
- `content-src/docs/systems/compute/meta.json`
- `content-src/docs/decisions/meta.json` (pages: index, accepted, rejected, pending)
- `content-src/docs/experiments/meta.json` (pages: index, active, completed, failed)
- `content-src/docs/projects/meta.json` (pages: index, ukb-pipeline)
- `content-src/docs/maps/meta.json`
- `content-src/docs/standards/meta.json`
- `content-src/docs/appendices/meta.json` (pages: templates, glossary, notation)

**Stub subfolder meta.json files (~18 files):**

- `concepts/mathematics/`, `concepts/statistics/`, `concepts/representation-learning/`, `concepts/machine-learning/`, `concepts/biomedical/`
- `methods/extraction/`, `methods/evaluation/`, `methods/reproducibility/`, `methods/build/`
- `systems/pipeline/`, `systems/data/`, `systems/runtime/`, `systems/security/`
- `decisions/accepted/`, `decisions/rejected/`, `decisions/pending/`
- `experiments/active/`, `experiments/completed/`, `experiments/failed/`

Per `1_implementation.md` section 6, projects also needs subfolders: `projects/ukb-pipeline/` (content exists at `projects/ukb-pipeline.mdx` level, no subfolder needed), `projects/gatehouse/`, `projects/stack-record/`. These get stub `meta.json` + index pairs.

### 3.2 Index page pairs (map notes for every section and subfolder)

Each top-level section and subfolder gets `index.mdx` + `index.meta.json` acting as a map note.

**Verbatim content from `2_starter_content.md` sections 4 and 7:**

- Root: `index.mdx` + `index.meta.json`
- `concepts/index`, `concepts/information-retrieval/index`
- `methods/index`, `methods/retrieval/index`
- `systems/index`, `systems/compute/index`
- `maps/index`, `standards/index`, `projects/index`

**Stub index pairs (following Map body template):**

- `decisions/index` (children: accepted, rejected, pending)
- `experiments/index` (children: active, completed, failed)
- Every stub subfolder in 3.1 gets an `index.mdx` + `index.meta.json`
- Note: `appendices/` does NOT get an index pair per spec (only has `templates`, `glossary`, `notation` pages)

### 3.3 Example content pages (body+sidecar pairs)

All verbatim from `2_starter_content.md`:

- `concepts/information-retrieval/cosine-similarity` -- section 4
- `concepts/information-retrieval/dot-product` -- section 8
- `concepts/information-retrieval/vector-similarity` -- section 8
- `methods/retrieval/rrf-pipeline` -- section 4
- `systems/compute/rabbitmq-central-broker` -- section 4
- `projects/ukb-pipeline` -- section 4
- `maps/open-loops` -- section 4
- `maps/learning-map` -- section 9
- `maps/domain-map` -- section 9
- `maps/method-map` -- section 9
- `maps/system-map` -- section 9

### 3.4 Standards content pages (all with full body content)

- `standards/closure-rule` -- **CRITICAL: use the FULL body from section 10 of `2_starter_content.md`**, not the placeholder. This includes: all 6 closure dimensions (U-L-D-A-E-M), score formula, interpretation table, per-type checklists (concept/method/system/decision/experiment), and the 5/6 promotion rule.
- `standards/metadata-schema` -- section 5
- `standards/writing-style` -- section 5
- `standards/note-quality-bar` -- section 5

### 3.5 Appendices

- `appendices/templates` (.mdx + .meta.json) -- Phase 4 deliverable
- `appendices/glossary` (.mdx + .meta.json) -- stub reference page per `1_implementation.md` section 6
- `appendices/notation` (.mdx + .meta.json) -- stub reference page per `1_implementation.md` section 6

Update `appendices/meta.json` pages array: `["templates", "glossary", "notation"]`

---

## Phase 4 -- Rich template page (appendices/templates.mdx)

### 4.1 Create `content-src/docs/appendices/templates.mdx` + `.meta.json`

This is the keystone deliverable. Per `0_overview.md`: "Templates are in `1_implementation.md` section 5 and documented in `content-src/docs/appendices/templates.mdx`." Per `2_starter_content.md` section 6: "The body of `templates.mdx` contains the full body + sidecar template pairs for all nine note types."

The page will use Fumadocs MDX artifacts for maximum readability:

- `**<Tabs>**` to switch between Body Template / Sidecar Template for each type
- `**<Steps>**` to show the rigid section order as a numbered creation guide
- `**<Callout type="warn">**` for mandatory fields ("Every note MUST have title, description, id, type") and hard invariants ("No frontmatter in authored MDX", "Materialiser will reject files missing a sidecar pair")
- `**<Callout type="info">**` for guidance tips
- `**<Callout type="error">**` for failure conditions
- `**<Accordion>**` for per-type closure checklists (expandable)
- **Code blocks** with `title="example.mdx"` and `title="example.meta.json"` for copy-paste templates
- `**<Cards>`** at the top linking to each of the 9 note type template sections

Each of the **9 templates** (concept, method, system, decision, experiment, project, map, standard, reference) will include:

1. The complete body section order from `1_implementation.md` section 5 with placeholder guidance text under each heading explaining what goes there and what cannot be missed
2. The complete sidecar JSON template from `1_implementation.md` section 4 with `{{CODE}}` and `{{TAG}}` placeholders
3. The closure checklist for that type from `1_implementation.md` section 9
4. Fumadocs-specific authoring tips:
  - "Use `$$..$$` for KaTeX math blocks" (concept/method)
  - "Use `<Steps>` for multi-step procedures" (method/experiment)
  - "Use `

```text ` for ASCII architecture diagrams" (system/concept)

- "Use `

```python title=example.py ` for titled code sketches" (method/system)

- "Use `<Callout>` for warnings and important notes in any page"
- "Use `// [!code highlight]` for line highlights in code blocks"
- "Use `<Tabs>` to show alternative approaches side by side"
- "Use `<Accordion>` for optional deep-dives within sections"

### 4.2 Writing standards integration

The templates page should reference the 7 writing rules from `1_implementation.md` section 8:

1. Define before explaining
2. Stable section order per note type
3. Plain-English interpretation for technical notes
4. One worked example minimum
5. Show drawbacks -- no note only sells the idea
6. Link outward to related notes and usage
7. Write for decision utility -- reader leaves knowing what to do

Plus type-specific additions:

- **Math notes:** equation, breakdown, variable defs, interpretation, example
- **System notes:** architecture diagram, config contract, failure modes, monitoring
- **Decision notes:** alternatives, tradeoffs, consequences, review trigger

---

## Phase 5 -- File-header docstrings

Add structured file-header docstrings to **every** `.ts`, `.tsx`, `.css`, and `.mjs` file in the repo, following the format defined in the "File header documentation standard" section above.

### 5.1 Existing files that need headers added (no logic changes)
- `app/layout.tsx` -- after the KaTeX CSS import line added in Phase 2
- `app/global.css` -- file-level header at the very top, before `@import`
- `app/docs/layout.tsx`
- `app/docs/[[...slug]]/page.tsx`
- `app/(home)/layout.tsx`
- `app/api/search/route.ts`
- `lib/source.ts` -- upgrade existing partial JSDoc to full PURPOSE/OWNS/TOUCH POINTS format
- `lib/layout.shared.tsx`
- `components/breadcrumb.tsx`
- `next.config.mjs`
- `postcss.config.mjs`

### 5.2 New files that get headers as part of creation
These are created in earlier phases but must include headers from the start:
- `scripts/materialize-fumadocs.ts`
- `lib/note-types.ts`
- `lib/closure.ts`
- `source.config.ts` (modified, header added)
- `components/mdx.tsx` (modified, header added)

### 5.3 Audit checklist
- Every `.ts`/`.tsx`/`.css`/`.mjs` file has a PURPOSE line
- Every file with exports has an OWNS section
- Every file with exports consumed elsewhere has a TOUCH POINTS section
- No redundant line-by-line narration comments added
- Existing good comments (like `global.css` section headers and `lib/source.ts` JSDoc) are preserved and enhanced, not replaced

---

## Phase 6 -- Landing page

### 6.1 Update `app/(home)/page.tsx`
Change description from "Minimal Fumadocs test site" to "Long-horizon learning system for concepts, methods, systems, decisions, and projects." Keep the existing button linking to `/docs`.

---

## Structural validation checklist

Before completion, verify these hard invariants from `0_overview.md`:

- Every `.mdx` under `content-src/` has a sibling `.meta.json`
- Every `.meta.json` under `content-src/` (page sidecars, not folder meta) has a sibling `.mdx`
- No `.mdx` under `content-src/` begins with `---`
- Every `.meta.json` sidecar has `title`, `description`, `id`, `type` fields (non-empty strings)
- Every folder under `content-src/docs/` has a `meta.json` with a `pages` array
- `.generated/` is in `.gitignore`
- `pnpm docs:materialize` runs without errors
- `source.config.ts` points at `.generated/docs` (not `content/docs`)
- `package.json` scripts chain materialiser before dev/build
- No inline `style={}` with hardcoded colours added to any component
- No new custom Fumadocs loaders, routing, or page-tree logic added
- `app/global.css` logic unchanged (only file-header comment added)
- `lib/source.ts` logic unchanged (only file-header upgraded)
- `lib/layout.shared.tsx` logic unchanged (only file-header added)
- `next.config.mjs` logic unchanged (only file-header added)
- `postcss.config.mjs` logic unchanged (only file-header added)
- `components/breadcrumb.tsx` logic unchanged (only file-header added)
- `app/docs/layout.tsx` logic unchanged (only file-header added)
- `app/docs/[[...slug]]/page.tsx` logic unchanged (only file-header added)
- `app/api/search/route.ts` logic unchanged (only file-header added)
- All 9 note type templates appear in `appendices/templates.mdx`
- Closure-rule page has the full body from section 10 (not a stub)
- Every `.ts`/`.tsx`/`.css`/`.mjs` file has a PURPOSE/OWNS/TOUCH POINTS header
- No redundant narration comments added (only structured headers)

---

## File count estimate

- ~31 folder `meta.json` files (13 specified + ~18 stub subfolders)
- ~30 `index.mdx` + `index.meta.json` pairs (sections + subfolders = ~60 files)
- 11 example content page pairs (= 22 files)
- 4 standards page pairs (= 8 files)
- 3 appendices page pairs (= 6 files)
- 3 new lib/script files
- 6 config/code file modifications
- Total: approximately **130 new files** + **6 modified files** + **1 deleted directory**

---

## Fumadocs MDX artifacts available for templates

Components registered in `components/mdx.tsx` (available without imports in any `.mdx`):


| Component                         | Use in templates                                                        |
| --------------------------------- | ----------------------------------------------------------------------- |
| `<Steps>` / `<Step>`              | Procedure sections in method/experiment templates                       |
| `<Callout>`                       | Warnings (`warn`), tips (`info`), errors (`error`), success (`success`) |
| `<Tabs>` / `<Tab>`                | Body vs sidecar template switching; alternative approaches              |
| `<Accordion>` / `<Accordions>`    | Expandable closure checklists                                           |
| `<Cards>` / `<Card>`              | Navigation cards in index/map pages                                     |
| `<Files>` / `<File>` / `<Folder>` | File tree diagrams showing content-src structure                        |
| `<TypeTable>`                     | Metadata field documentation tables                                     |
| `<ImageZoom>`                     | Zoomable images for architecture diagrams                               |


Code block features (via rehype-code, no component needed):

- `

```ts title="filename.ts" ` -- titled code blocks

- `

```ts lineNumbers ` -- line numbers

- `// [!code highlight]` -- line highlighting
- `// [!code --]` / `// [!code ++]` -- diff markers
- `// [!code focus]` -- focus lines
- `$$..$$` for KaTeX math blocks (via remark-math + rehype-katex)

---

## Build order (per 1_implementation.md section 10)

This is the execution order within the phases:

1. `scripts/materialize-fumadocs.ts`
2. `lib/note-types.ts` + `lib/closure.ts`
3. `source.config.ts` (point at `.generated/docs`)
4. `lib/source.ts` (no changes needed -- already correct)
5. Root `content-src/docs/meta.json`
6. Standards section (closure-rule, metadata-schema, writing-style, note-quality-bar)
7. One concept pair (cosine-similarity)
8. One method pair (rrf-pipeline)
9. One system pair (rabbitmq-central-broker)
10. Maps section (especially open-loops)
11. `app/api/search/route.ts` (no changes needed -- already correct)

