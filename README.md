# Stack Record

A long-horizon personal knowledge system built on [Fumadocs](https://fumadocs.vercel.app/) and [Next.js](https://nextjs.org/). Nine structured note types, a sidecar metadata layer, closure scoring, and a materialiser pipeline that turns body-only MDX + JSON sidecars into a full documentation site with search, math rendering, and cross-linked navigation.

One custom build step. Everything else is standard Fumadocs.

> **What this is for:** building a second brain that compounds over years -- not a wiki, not a blog, not a note dump. Every note has a type, a template, a quality score, and explicit links to related notes. The system is designed so that writing one note improves every note it connects to.

---

## What You Get

| | |
|---|---|
| **Nine note types** | Concepts, Methods, Systems, Decisions, Experiments, Projects, Maps, Standards, and References -- each with a fixed template and a sidecar metadata schema. |
| **Closure scoring** | Every note is scored across six dimensions (upward links, lateral links, downward links, applied links, epistemic honesty, maintenance). Score 6/6 = closed. The system tracks what's incomplete. |
| **Sidecar metadata** | Page metadata lives in `.meta.json` files alongside body-only `.mdx` files. A build-time materialiser merges them into frontmatter. No custom Fumadocs loaders or plugins. |
| **Maps for orientation** | Map notes (MOCs) provide navigation across domains -- learning paths, domain overviews, method inventories, system architecture maps, and an open-loops tracker. |
| **Full Fumadocs features** | Sidebar navigation, full-text search, KaTeX math, MDX components (Callout, Steps, Tabs, Accordion, Files, Cards, TypeTable, ImageZoom), dark mode, and responsive layout -- all out of the box. |
| **Obsidian authoring** | Write notes in Obsidian with wiki-link syntax, then publish through the Fumadocs pipeline. Scripts for note creation, copilot prompts, and KG queries included. |
| **Knowledge graph tooling** | Python tools for building and querying a SQLite knowledge graph from sidecar metadata -- find orphans, audit links, traverse prerequisites. |
| **Library registry** | A verified inventory of libraries and tools, synced from GitHub/PyPI, displayed in a searchable table component. |
| **Docker deployment** | Single-command production build with `docker compose up`. |

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/donphi/stack-record.git
cd stack-record

# 2. Build and run
docker compose up --build

# Open http://localhost:3000
```

> **Prerequisites:** [Docker](https://www.docker.com/) and Docker Compose. That's it. The build handles dependency installation, content materialisation, and the Next.js production build inside a multi-stage Dockerfile. The repo ships with starter content across all nine note types so the site works immediately after clone.

---

## Architecture

```
content-src/docs/              ← what you edit (body-only .mdx + .meta.json sidecars)
    ├── (01-navigation)/maps/
    ├── (02-knowledge)/concepts/, methods/, systems/
    ├── (03-operations)/projects/, decisions/, experiments/
    ├── (04-governance)/standards/, appendices/
    └── (05-inbox)/notes/

        ↓  docker compose up --build (materialise + build)

.generated/docs/               ← what Fumadocs reads (frontmatter + body, gitignored)

        ↓  served at localhost:3000

http://localhost:3000           ← the site
```

Folder groups `(01-navigation)` through `(05-inbox)` organise the filesystem but are transparent to URLs. Published paths look like `/docs/concepts/...`, `/docs/methods/...`, etc.

The materialiser (`scripts/materialize-fumadocs.ts`) is the **only custom code** in the system. It reads each `.mdx` + `.meta.json` pair, merges the sidecar fields into YAML frontmatter, and writes the result to `.generated/docs/`. Fumadocs handles everything else.

---

## Content Structure

### Note Types

| Type | Section | Purpose | Template |
|------|---------|---------|----------|
| Concept | `concepts/` | Atomic ideas and theory | What, Why, Where, Equation, Example, Drawbacks |
| Method | `methods/` | Repeatable procedures | What, Why, Inputs, Outputs, Procedure, Code sketch |
| System | `systems/` | Concrete implementations | Architecture, Config contract, Failure modes, Monitoring |
| Decision | `decisions/` | Architecture decision records | Context, Options, Tradeoffs, Consequences, Review trigger |
| Experiment | `experiments/` | Hypotheses and results | Hypothesis, Setup, Procedure, Results, Threats |
| Project | `projects/` | Project-level synthesis | Goal, Key methods, Key systems, Status, Roadmap |
| Map | `maps/` | Navigation and orientation | What this map covers, Structure, Gaps |
| Standard | `standards/` | Rules for the system itself | Purpose, Applies to, Rules, Failure conditions |
| Reference | `appendices/` | Templates, glossary, notation | Varies by reference type |

### File Pairing

Every content page is two files:

```
cosine-similarity/
├── index.mdx           ← body content (no frontmatter, never starts with ---)
└── index.meta.json     ← structured metadata (title, type, tags, graph links, closure score)
```

The materialiser rejects any `.mdx` that starts with `---` and any sidecar without a matching body.

### Closure Scoring

Every note is scored across six binary dimensions:

| Dim | Name | Satisfied when |
|-----|------|----------------|
| U | Upward | Links to at least one parent map |
| L | Lateral | Links to at least two peer notes or prerequisites |
| D | Downward | Links to at least one child, example, or comparison |
| A | Applied | Links to at least one project, system, or experiment |
| E | Epistemic | States limitations, failure modes, or open questions |
| M | Maintenance | Has status, review cycle, and last-reviewed date |

Score 6/6 = closed. 4-5 = usable. 0-3 = orphan. No note promoted to `evergreen` below 5/6.

---

## Obsidian Integration

Stack Record can be authored from [Obsidian](https://obsidian.md/) using wiki-link syntax. The `obsidian/` directory contains everything needed to set up a parallel authoring workflow:

| What | Where |
|------|-------|
| Setup guide | `obsidian/README.md` |
| Note creation script | `obsidian/scripts/create-note-pair.js` |
| Note template | `obsidian/scripts/_new-note.md` |
| Copilot prompts | `obsidian/copilot/copilot-custom-prompts/` |
| KG query reference | Integrated with `tools/kg-builder/` |

### How it works

1. Open the `content-src/docs/` folder as an Obsidian vault.
2. Write notes using `[[wiki_link]]` syntax -- the materialiser resolves these to real links at build time.
3. Run the note creation script to generate properly paired `.mdx` + `.meta.json` files.
4. Rebuild with `docker compose up --build` to materialise and preview.

Obsidian's graph view, backlinks, and search work naturally with the wiki-link syntax. The `.obsidian/` config directory is gitignored.

---

## MDX Components

All components are registered globally -- no imports needed in `.mdx` files.

| Component | Use case |
|-----------|----------|
| `<Callout>` | Tips, warnings, errors, ideas (`type="info"`, `"warn"`, `"error"`, `"success"`, `"idea"`) |
| `<Steps>` / `<Step>` | Sequential procedures with a vertical progress line |
| `<Tabs>` / `<Tab>` | Switchable panels for comparisons or multi-language code |
| `<Accordions>` / `<Accordion>` | Collapsible sections for optional detail |
| `<Files>` / `<Folder>` / `<File>` | Interactive file tree diagrams |
| `<Cards>` / `<Card>` | Navigation link cards with descriptions |
| `<TypeTable>` | Structured property documentation with types and defaults |
| `<ImageZoom>` | Click-to-zoom images for diagrams |
| `$$...$$` | Display math (KaTeX) |
| `$...$` | Inline math (KaTeX) |
| `[[wiki_link]]` | Cross-references resolved at build time |

See the [Writing Style standard](/docs/standards/writing-style) for live demos and placement guidance for each note type.

---

## Tools

### Knowledge Graph Builder (`tools/kg-builder/`)

Builds a SQLite knowledge graph from sidecar metadata. Query it to find orphan notes, audit prerequisite chains, and traverse the graph.

### Knowledge Graph Extractor (`tools/kg-extractor/`)

Extracts structured data from document corpora for ingestion into the knowledge system.

### Library Registry (`tools/lib-registry/`)

Syncs library metadata from GitHub and PyPI into a JSON registry displayed by the `<LibraryTable>` component. Tracks versions, update dates, and pipeline section tags.

---

## Project Structure

```
stack-record/
├── app/                        ← Next.js app (layouts, pages, API routes)
├── components/                 ← React components (MDX registry, library table)
├── lib/                        ← Shared utilities (source config, closure scoring, note types)
├── scripts/
│   └── materialize-fumadocs.ts ← The one custom build step
├── content-src/docs/           ← Authored content (body .mdx + .meta.json sidecars)
│   ├── (01-navigation)/maps/
│   ├── (02-knowledge)/concepts/, methods/, systems/
│   ├── (03-operations)/projects/, decisions/, experiments/
│   ├── (04-governance)/standards/, appendices/
│   └── (05-inbox)/notes/
├── .generated/docs/            ← Build output (gitignored)
├── tools/                      ← Python tooling (KG builder, KG extractor, lib registry)
├── obsidian/                   ← Obsidian authoring setup (scripts, prompts)
├── 0_overview.md               ← Architecture documentation
├── 1_implementation.md         ← Contracts and templates
├── 2_starter_content.md        ← Bootstrap content reference
├── Dockerfile
├── docker-compose.yml
└── package.json
```

---

## Creating a New Note

Use the template files in any section's `_template/` folder:

```bash
# Example: create a new concept note
cp -r "content-src/docs/(02-knowledge)/concepts/_template" \
      "content-src/docs/(02-knowledge)/concepts/your-domain/your-concept"

# Rename the template files
mv your-concept/example.mdx.template your-concept/index.mdx
mv your-concept/example.meta.json.template your-concept/index.meta.json

# Edit both files, then add the slug to the parent meta.json pages array
```

Or use the Obsidian note creation script:

```bash
node obsidian/scripts/create-note-pair.js concept your-domain your-concept
```

---

## Screenshots

### Light Mode

<p align="center">
  <img src="doc/images/light-home.png" alt="Home page -- light mode" width="800" />
</p>

<p align="center"><em>Home page with navigation to all sections.</em></p>

<p align="center">
  <img src="doc/images/light-concept.png" alt="Concept note -- light mode" width="800" />
</p>

<p align="center"><em>A concept note with KaTeX math, callouts, and cross-links.</em></p>

<p align="center">
  <img src="doc/images/light-sidebar.png" alt="Sidebar navigation -- light mode" width="800" />
</p>

<p align="center"><em>Sidebar navigation across all nine sections.</em></p>

### Dark Mode

<p align="center">
  <img src="doc/images/dark-home.png" alt="Home page -- dark mode" width="800" />
</p>

<p align="center"><em>Home page in dark mode.</em></p>

<p align="center">
  <img src="doc/images/dark-concept.png" alt="Concept note -- dark mode" width="800" />
</p>

<p align="center"><em>Same concept note in dark mode with syntax-highlighted code blocks.</em></p>

<p align="center">
  <img src="doc/images/dark-sidebar.png" alt="Sidebar navigation -- dark mode" width="800" />
</p>

<p align="center"><em>Sidebar in dark mode.</em></p>

> **To add your own screenshots:** run `docker compose up --build`, take screenshots of the pages listed above in both light and dark mode, save them to `doc/images/` with the filenames shown, and they'll appear here automatically.

---

## Built With

- [Fumadocs](https://fumadocs.vercel.app/) -- documentation framework (MIT)
- [Next.js](https://nextjs.org/) -- React framework (MIT)
- [Tailwind CSS](https://tailwindcss.com/) -- utility-first CSS (MIT)
- [KaTeX](https://katex.org/) -- math rendering (MIT)
- [MDX](https://mdxjs.com/) -- Markdown + JSX (MIT)

---

## License

MIT -- see [LICENSE](LICENSE) for details.

This project uses [Fumadocs](https://fumadocs.vercel.app/) which is also MIT licensed. The content you create with this system is yours.

---

<p align="center">
  <sub>Built by <a href="https://github.com/donphi">donphi</a></sub>
</p>
