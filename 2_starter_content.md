# Stack Record — Starter Content

Read `0_overview.md` and `1_implementation.md` first. This file contains the
actual contents of every file an LLM needs to create or modify to bring the
sidecar architecture to life. Copy verbatim unless adapting to existing repo
state.

---

## 1. Build tooling

### `scripts/materialize-fumadocs.ts`

```ts
import fs from 'node:fs/promises';
import path from 'node:path';
import matter from 'gray-matter';

const SRC_DIR = path.resolve('content-src/docs');
const OUT_DIR = path.resolve('.generated/docs');

async function rmrf(dir: string): Promise<void> {
  await fs.rm(dir, { recursive: true, force: true });
}

async function ensureDir(dir: string): Promise<void> {
  await fs.mkdir(dir, { recursive: true });
}

async function listFilesRecursive(dir: string): Promise<string[]> {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const out: string[] = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...(await listFilesRecursive(full)));
    } else {
      out.push(full);
    }
  }
  return out;
}

function isPageBodyFile(file: string): boolean {
  return file.endsWith('.md') || file.endsWith('.mdx');
}

function isFolderMetaFile(file: string): boolean {
  return path.basename(file) === 'meta.json';
}

function isPageMetaFile(file: string): boolean {
  return file.endsWith('.meta.json') && path.basename(file) !== 'meta.json';
}

function toPosix(p: string): string {
  return p.split(path.sep).join('/');
}

function relativeFromSrc(file: string): string {
  return toPosix(path.relative(SRC_DIR, file));
}

function parsePageMeta(raw: unknown, file: string): Record<string, unknown> {
  if (!raw || typeof raw !== 'object') {
    throw new Error(`Invalid page meta object: ${file}`);
  }
  const obj = raw as Record<string, unknown>;
  const requiredStrings = ['title', 'description', 'id', 'type'] as const;
  for (const key of requiredStrings) {
    if (typeof obj[key] !== 'string' || (obj[key] as string).trim() === '') {
      throw new Error(`Missing required "${key}" in ${file}`);
    }
  }
  return obj;
}

function expectedPageMetaPath(docFile: string): string {
  const ext = path.extname(docFile);
  return docFile.slice(0, -ext.length) + '.meta.json';
}

function outputPathForSourceFile(srcFile: string): string {
  const rel = path.relative(SRC_DIR, srcFile);
  if (isPageMetaFile(srcFile)) {
    throw new Error(`Page meta sidecars are not copied directly: ${srcFile}`);
  }
  return path.join(OUT_DIR, rel);
}

async function copyFolderMeta(file: string): Promise<void> {
  const out = outputPathForSourceFile(file);
  await ensureDir(path.dirname(out));
  await fs.copyFile(file, out);
}

async function materializePage(docFile: string): Promise<void> {
  const metaFile = expectedPageMetaPath(docFile);
  try {
    await fs.access(metaFile);
  } catch {
    throw new Error(
      `Missing sidecar meta file for page body:\n` +
      `  body: ${relativeFromSrc(docFile)}\n` +
      `  expected meta: ${relativeFromSrc(metaFile)}`
    );
  }
  const [body, metaRaw] = await Promise.all([
    fs.readFile(docFile, 'utf8'),
    fs.readFile(metaFile, 'utf8'),
  ]);
  if (body.trimStart().startsWith('---')) {
    throw new Error(`Authored body file must not contain frontmatter: ${relativeFromSrc(docFile)}`);
  }
  const parsedMeta = parsePageMeta(JSON.parse(metaRaw), relativeFromSrc(metaFile));
  const compiled = matter.stringify(body.trimStart(), parsedMeta);
  const out = outputPathForSourceFile(docFile);
  await ensureDir(path.dirname(out));
  await fs.writeFile(out, compiled, 'utf8');
}

async function main(): Promise<void> {
  await rmrf(OUT_DIR);
  await ensureDir(OUT_DIR);
  const files = await listFilesRecursive(SRC_DIR);
  const docs = files.filter(isPageBodyFile);
  const folderMetas = files.filter(isFolderMetaFile);
  const pageMetas = files.filter(isPageMetaFile);

  for (const metaFile of pageMetas) {
    const possibleMdx = metaFile.replace(/\.meta\.json$/, '.mdx');
    const possibleMd = metaFile.replace(/\.meta\.json$/, '.md');
    const hasBody = files.includes(possibleMdx) || files.includes(possibleMd);
    if (!hasBody) {
      throw new Error(`Orphan page meta file without matching body:\n  ${relativeFromSrc(metaFile)}`);
    }
  }

  for (const file of folderMetas) {
    await copyFolderMeta(file);
  }
  for (const docFile of docs) {
    await materializePage(docFile);
  }
  console.log(`Materialized ${docs.length} page(s) into ${OUT_DIR}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
```

### `lib/note-types.ts`

```ts
export type NoteType =
  | 'map' | 'concept' | 'method' | 'system'
  | 'decision' | 'experiment' | 'project'
  | 'standard' | 'reference';

export type ClosureStatus = 'open' | 'partial' | 'closed' | 'archived';
export type ReviewCycle = 'weekly' | 'monthly' | 'quarterly' | 'yearly' | 'never';

export interface BaseNoteMeta {
  title: string;
  description: string;
  id: string;
  type: NoteType;
  domain?: string;
  status?: string;
  tags?: string[];
  aliases?: string[];
  parent_maps?: string[];
  prerequisites?: string[];
  children?: string[];
  related_notes?: string[];
  related_methods?: string[];
  related_systems?: string[];
  related_projects?: string[];
  review_cycle?: ReviewCycle;
  last_reviewed?: string;
  closure_score?: number;
  closure_status?: ClosureStatus;
  open_questions?: string[];
}
```

### `lib/closure.ts`

```ts
import type { BaseNoteMeta } from './note-types';

export interface ClosureBreakdown {
  upward: 0 | 1;
  lateral: 0 | 1;
  downward: 0 | 1;
  applied: 0 | 1;
  epistemic: 0 | 1;
  maintenance: 0 | 1;
  total: number;
}

export function scoreClosure(meta: BaseNoteMeta): ClosureBreakdown {
  const upward: 0 | 1 = meta.parent_maps && meta.parent_maps.length > 0 ? 1 : 0;
  const lateralCount = (meta.related_notes?.length ?? 0) + (meta.prerequisites?.length ?? 0);
  const lateral: 0 | 1 = lateralCount >= 2 ? 1 : 0;
  const downward: 0 | 1 = meta.children && meta.children.length > 0 ? 1 : 0;
  const appliedCount =
    (meta.related_methods?.length ?? 0) +
    (meta.related_systems?.length ?? 0) +
    (meta.related_projects?.length ?? 0);
  const applied: 0 | 1 = appliedCount >= 1 ? 1 : 0;
  const epistemic: 0 | 1 = meta.open_questions && meta.open_questions.length > 0 ? 1 : 0;
  const maintenance: 0 | 1 = meta.review_cycle && meta.last_reviewed ? 1 : 0;
  const total = upward + lateral + downward + applied + epistemic + maintenance;
  return { upward, lateral, downward, applied, epistemic, maintenance, total };
}
```

---

## 2. Root config changes

### `source.config.ts`

```ts
import { defineDocs, defineConfig } from 'fumadocs-mdx/config';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

export const { docs, meta } = defineDocs({
  dir: '.generated/docs',
});

export default defineConfig({
  mdxOptions: {
    remarkPlugins: [remarkMath],
    rehypePlugins: (v) => [rehypeKatex, ...v],
  },
});
```

### `.gitignore` additions

```
.generated/
```

---

## 3. Folder `meta.json` files

### `content-src/docs/meta.json`

```json
{
  "title": "Stack Record",
  "pages": [
    "index",
    "---Navigation---",
    "...(01-navigation)",
    "---Knowledge---",
    "...(02-knowledge)",
    "---Operations---",
    "...(03-operations)",
    "---Governance---",
    "...(04-governance)",
    "---Inbox---",
    "...(05-inbox)"
  ]
}
```

### `content-src/docs/concepts/meta.json`

```json
{
  "title": "Concepts",
  "icon": "Sparks",
  "pages": [
    "mathematics", "statistics", "information-retrieval",
    "representation-learning", "machine-learning", "biomedical"
  ]
}
```

### `content-src/docs/concepts/information-retrieval/meta.json`

```json
{
  "title": "Information Retrieval",
  "pages": ["index", "cosine-similarity", "dot-product", "vector-similarity"]
}
```

### `content-src/docs/methods/meta.json`

```json
{
  "title": "Methods",
  "pages": ["index", "extraction", "retrieval", "evaluation", "reproducibility", "build"]
}
```

### `content-src/docs/methods/retrieval/meta.json`

```json
{
  "title": "Retrieval",
  "pages": ["index", "rrf-pipeline"]
}
```

### `content-src/docs/systems/meta.json`

```json
{
  "title": "Systems",
  "pages": ["index", "pipeline", "data", "compute", "runtime", "security"]
}
```

### `content-src/docs/systems/compute/meta.json`

```json
{
  "title": "Compute",
  "pages": ["index", "rabbitmq-central-broker"]
}
```

### `content-src/docs/decisions/meta.json`

```json
{
  "title": "Decisions",
  "pages": ["index", "accepted", "rejected", "pending"]
}
```

### `content-src/docs/experiments/meta.json`

```json
{
  "title": "Experiments",
  "pages": ["index", "active", "completed", "failed"]
}
```

### `content-src/docs/projects/meta.json`

```json
{
  "title": "Projects",
  "icon": "ReportColumns",
  "pages": []
}
```

### `content-src/docs/maps/meta.json`

```json
{
  "title": "Maps",
  "pages": ["index", "learning-map", "domain-map", "method-map", "system-map", "open-loops"]
}
```

### `content-src/docs/standards/meta.json`

```json
{
  "title": "Standards",
  "pages": ["index", "closure-rule", "metadata-schema", "writing-style", "note-quality-bar"]
}
```

### `content-src/docs/appendices/meta.json`

```json
{
  "title": "Appendices",
  "pages": ["templates"]
}
```

---

## 4. Example page pairs

Each page is an `.mdx` (body only) + `.meta.json` (sidecar) pair.

### `content-src/docs/index.meta.json`

```json
{
  "title": "Stack Record",
  "description": "Long-horizon learning system for concepts, methods, systems, decisions, and projects.",
  "id": "HOME-0001",
  "type": "map",
  "domain": "global",
  "status": "evergreen",
  "tags": ["map/home"],
  "children": ["learning-map", "domain-map", "method-map", "system-map", "open-loops"],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/index.mdx`

```mdx
# Stack Record

## Start here

- [Learning Map](/docs/maps/learning-map)
- [Domain Map](/docs/maps/domain-map)
- [Method Map](/docs/maps/method-map)
- [System Map](/docs/maps/system-map)
- [Open Loops](/docs/maps/open-loops)

## Sections

- [Concepts](/docs/concepts)
- [Methods](/docs/methods)
- [Systems](/docs/systems)
- [Projects](/docs/projects)
- [Decisions](/docs/decisions)
- [Experiments](/docs/experiments)
- [Standards](/docs/standards)
```

### `content-src/docs/concepts/information-retrieval/cosine-similarity/index.meta.json`

```json
{
  "title": "Cosine Similarity",
  "description": "A similarity measure based on the angle between two vectors.",
  "id": "C-IR-0007",
  "type": "concept",
  "domain": "information_retrieval",
  "status": "evergreen",
  "tags": ["concept/ir", "concept/maths"],
  "aliases": ["cosine similarity", "cosine score"],
  "parent_maps": ["MOC_Similarity_Metrics"],
  "prerequisites": ["vectors", "dot_product", "magnitude"],
  "children": ["cosine_vs_euclidean_vs_dot"],
  "related_notes": ["vector_similarity"],
  "related_methods": ["dense_retrieval"],
  "related_systems": ["faiss_setup"],
  "related_projects": [],
  "review_cycle": "monthly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": ["When does dot product outperform cosine in normalized embedding pipelines?"]
}
```

### `content-src/docs/concepts/information-retrieval/cosine-similarity/index.mdx`

````mdx
## What this is

Cosine similarity measures alignment between two vectors. It captures direction more than raw magnitude.

## Why this matters

In many embedding systems, semantic similarity is better represented by direction than by vector length.

## Where this fits

- Parent map: [[MOC_Similarity_Metrics]]
- Prerequisites: [[vectors]], [[dot_product]], [[magnitude]]
- Used in method: [[dense_retrieval]]
- Used in system: [[faiss_setup]]
- Used in project: your project here

## Core idea

Two vectors can have different sizes but still point in nearly the same direction. Cosine similarity captures that directional relationship.

## Equation

$$
\cos(\theta) = \frac{\mathbf{a}\cdot\mathbf{b}}{\|\mathbf{a}\|\|\mathbf{b}\|}
$$

## Breakdown

### Terms

- $\mathbf{a}\cdot\mathbf{b}$ = dot product
- $\|\mathbf{a}\|$ = magnitude of vector `a`
- $\|\mathbf{b}\|$ = magnitude of vector `b`

### What the equation is really doing

It divides the dot product by the product of the two vector lengths, so the final score mainly reflects angular alignment.

## Plain-English explanation

Cosine asks: "Are these vectors pointing in the same direction?"

## Worked example

If `a = [1, 1]` and `b = [2, 2]`, the vectors have different sizes but the same direction, so cosine similarity is 1.

## ASCII diagram

```text
y
^
|        b
|      /
|    /
|  /   a
|/
+------------> x
````

## Why this is used

It is useful when vector length is less meaningful than vector direction.

## Benefits

* reduces magnitude distortion
* intuitive for embeddings
* widely used in retrieval

## Drawbacks and failure modes

* discards magnitude information
* can hide meaningful norm differences
* not automatically the best metric in every embedding setup

## Where I have used it

* Your project — embedding similarity comparisons
* [[faiss_setup]] — normalized vector search

## Questions this note answers

* What does cosine similarity measure?
* Why does normalization matter?
* When is cosine better than dot product?

## Related notes

* [[dot_product]]
* [[vector_similarity]]
* [[cosine_vs_euclidean_vs_dot]]

## Open questions

* How often do biomedical embedders encode useful signal in vector norm?

## Review

* Next review target: add ANN-specific implications

````

### `content-src/docs/methods/retrieval/rrf-pipeline/index.meta.json`

```json
{
  "title": "Reciprocal Rank Fusion Pipeline",
  "description": "A rank-fusion method for combining retrieval systems without forcing raw score comparability.",
  "id": "M-RET-0012",
  "type": "method",
  "domain": "retrieval",
  "status": "evergreen",
  "tags": ["method/retrieval"],
  "parent_maps": ["Method_Map"],
  "related_notes": ["rank_fusion", "score_distributions", "threshold_selection"],
  "related_methods": [],
  "related_systems": ["rrf_pipeline"],
  "related_projects": [],
  "review_cycle": "monthly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": ["Should weighting ever be justified when judges operate on incompatible inductive biases?"]
}
```

### `content-src/docs/methods/retrieval/rrf-pipeline/index.mdx`

````mdx
## What this method is

A retrieval-combination method that merges ranked outputs from multiple judges using position rather than raw score comparability.

## Why this is used

Different retrieval systems often produce scores on incompatible scales. Rank fusion avoids pretending those scales are directly comparable.

## Where this fits

- Parent map: [[Method_Map]]
- Uses concepts: [[rank_fusion]], [[score_distributions]]
- Implemented in: [[rrf_pipeline]]
- Used in project: your project here

## Inputs

- ranked candidate lists
- fusion constant

## Outputs

- fused ranked list
- optional fused score

## Procedure

1. run multiple retrieval judges
2. rank candidates within each judge
3. convert rank to reciprocal contribution
4. sum contributions across judges

## Formal rule or formula

$$
RRF(d) = \sum_i \frac{1}{k + rank_i(d)}
$$

## Why it works

Agreement across judges is preserved without assuming that raw score scales are directly compatible.

## Code sketch

```python
def rrf(rank_lists: list[list[str]], k: int = 60) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in rank_lists:
        for idx, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + idx)
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
````

## Benefits

* robust across incompatible scorers
* simple to reason about

## Drawbacks

* discards magnitude information
* depends on upstream ranking quality

## Failure modes

* mixing boolean gates into continuous fusion
* too few candidates from one judge
* poor diversity across judges

## Where I have used it

* Your project — combining multiple semantic judges

## Validation and evidence

* [[two_judge_evaluation]] — precision-oriented validation

## Questions this note answers

* How do I combine incompatible rankers?
* Why not average raw scores?

## Related notes

* [[rank_fusion]]
* [[rrf_pipeline]]
* [[two_judge_evaluation]]

## Open questions

* Need a weighted-fusion comparison experiment.

## Review

* Next review target: add score-normalization comparison

````

### `content-src/docs/systems/compute/rabbitmq-central-broker/index.meta.json`

```json
{
  "title": "RabbitMQ Central Broker",
  "description": "Central queue broker coordinating competing GPU and CPU consumers across the pipeline.",
  "id": "S-CMP-0004",
  "type": "system",
  "domain": "compute",
  "status": "active",
  "tags": ["system/compute"],
  "parent_maps": ["System_Map"],
  "related_notes": ["naming_contracts", "contract_system"],
  "related_methods": ["gpu_dispatch", "gpu_worker"],
  "related_systems": [],
  "related_projects": [],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": ["Should some stages move to pull-batch processing instead of per-job dispatch?"]
}
```

### `content-src/docs/systems/compute/rabbitmq-central-broker/index.mdx`

````mdx
## What this system is

A single central message broker coordinating job dispatch and worker consumption for pipeline stages.

## Why this exists

It decouples dispatch from execution and lets multiple workers compete for jobs without hardwiring producers to specific consumers.

## Where this fits

- Parent map: [[System_Map]]
- Implements: [[gpu_dispatch]]
- Used in project: your project here

## Architecture

```text
Dispatch Script
    |
    v
[ RabbitMQ Queue ] ---> Worker A
        |             Worker B
        |             Worker C
        v
   Completion Signal / Sentinel
````

## Components

* producer / dispatch layer
* queue
* consumers / workers

## Configuration contract

* queue name must match resources config
* worker subscription must match exact queue name
* payload schema must validate before execution

## Why it is used

It amortizes model loading and simplifies horizontal scale-out.

## Benefits

* scalable
* decoupled
* supports competing consumers

## Drawbacks

* naming mistakes are painful
* distributed debugging is harder

## Failure modes

* wrong queue name
* stale worker version
* payload schema drift

## Monitoring

* queue depth
* consumer count
* average job latency

## Where I have used it

* Your project — persistent GPU worker architecture

## Related notes

* [[gpu_dispatch]]
* [[gpu_worker]]
* [[naming_contracts]]

## Open questions

* Need dead-letter queue strategy note.

## Review

* Next review target: add retry topology

````

### `content-src/docs/maps/open-loops/index.meta.json`

```json
{
  "title": "Open Loops",
  "description": "Active unresolved questions and incomplete knowledge chains across Stack Record.",
  "id": "MAP-OPEN-0001",
  "type": "map",
  "domain": "global",
  "status": "active",
  "tags": ["map/open-loops"],
  "children": [],
  "review_cycle": "weekly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": ["How should low-closure notes be surfaced automatically?"]
}
```

### `content-src/docs/maps/open-loops/index.mdx`

```mdx
# Open Loops

## High-priority open loops

- cosine similarity vs dot product under normalized biomedical embeddings
- exact criteria for when norm magnitude should be preserved
- dead-letter queue strategy for worker architecture

## Notes below closure threshold

- [[cosine_vs_euclidean_vs_dot]]
- [[faiss_setup]]
- [[two_judge_evaluation]]

## Missing bridge notes

- [[normalisation]]
- [[ann_search_tradeoffs]]

## Review rule

Any note below `5/6` closure must appear here until repaired, merged, or archived.
```

### `content-src/docs/projects/ukb-pipeline/index.meta.json`

```json
{
  "title": "My Research Pipeline",
  "description": "End-to-end pipeline for data extraction and processing.",
  "id": "P-PROJ-0001",
  "type": "project",
  "domain": "project",
  "status": "active",
  "tags": ["project/ukb"],
  "related_notes": ["cosine_similarity", "rank_fusion"],
  "related_methods": ["disease_extraction", "rrf_pipeline"],
  "related_systems": ["rabbitmq_central_broker", "contract_system"],
  "related_projects": [],
  "review_cycle": "monthly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": ["Need thresholding evidence note.", "Need ANN tradeoff note."]
}
```

### `content-src/docs/projects/ukb-pipeline/index.mdx`

```mdx
## What this project is

A large-scale document processing and extraction system for biomedical literature.

## Why it exists

To extract, normalize, validate, and analyze domain-specific mentions across a large document corpus.

## Scope

It covers acquisition, parsing, extraction, validation, and structured outputs.

## Key concepts

- [[cosine_similarity]]
- [[rank_fusion]]

## Key methods

- [[disease_extraction]]
- [[rrf_pipeline]]

## Key systems

- [[rabbitmq_central_broker]]
- [[contract_system]]

## Key decisions

- [[two_judge_system]]
- [[use_fumadocs_as_publishing_layer]]

## Status

Active.

## Lessons learned

- architecture and coordination matter as much as model choice
- score comparability must not be assumed blindly

## Open loops

- thresholding evidence note
- ANN tradeoff note
```

---

## 5. Standards content

The standards section defines the rules of the system itself. Each page
follows the standard body template.

### `content-src/docs/standards/closure-rule/index.meta.json`

```json
{
  "title": "Closure Rule",
  "description": "Operational rule for determining whether a note is complete and connected.",
  "id": "STD-CLS-0001",
  "type": "standard",
  "domain": "standards",
  "status": "enforced",
  "tags": ["standard/closure"],
  "review_cycle": "yearly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/standards/closure-rule/index.mdx`

See `0_overview.md` section 5 for the closure dimensions (U-L-D-A-E-M).
The full closure-rule body content is in the original `1_main_idea.md`
sections 10 and should be transcribed using the standard body template,
covering: dimensions, score formula, interpretation, per-type checklists,
and the 5/6 promotion rule.

### `content-src/docs/standards/metadata-schema/index.meta.json`

```json
{
  "title": "Metadata Schema",
  "description": "Required page-sidecar metadata model for all Stack Record note types.",
  "id": "STD-META-0001",
  "type": "standard",
  "domain": "standards",
  "status": "enforced",
  "tags": ["standard/metadata"],
  "review_cycle": "yearly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/standards/metadata-schema/index.mdx`

```mdx
# Metadata Schema

## Required fields

- `title`, `description`, `id`, `type`, `status`, `review_cycle`

## Allowed note types

- `map`, `concept`, `method`, `system`, `decision`, `experiment`, `project`, `standard`, `reference`

## Status values

- `draft`, `active`, `evergreen`, `accepted`, `rejected`, `completed`, `superseded`, `archived`

## Review cycles

- `weekly`, `monthly`, `quarterly`, `yearly`, `never`

## Closure fields

`closure_score` is 0–6. `closure_status` is one of: `open`, `partial`, `closed`, `archived`.
```

### `content-src/docs/standards/writing-style/index.meta.json`

```json
{
  "title": "Writing Style",
  "description": "Writing standard for all Stack Record notes.",
  "id": "STD-WRITE-0001",
  "type": "standard",
  "domain": "standards",
  "status": "enforced",
  "tags": ["standard/writing"],
  "review_cycle": "yearly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/standards/writing-style/index.mdx`

```mdx
# Writing Style

## Core rule

Every note must be readable by future-you after a long gap.

## Mandatory writing rules

### 1. Define before explaining
### 2. Use stable section order
### 3. Use plain-English interpretation
### 4. Show one worked example
### 5. Show drawbacks
### 6. Link outward
### 7. Write for decision utility
```

### `content-src/docs/standards/note-quality-bar/index.meta.json`

```json
{
  "title": "Note Quality Bar",
  "description": "Minimum standard for promoting a note from draft to evergreen.",
  "id": "STD-QUAL-0001",
  "type": "standard",
  "domain": "standards",
  "status": "enforced",
  "tags": ["standard/quality"],
  "review_cycle": "yearly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/standards/note-quality-bar/index.mdx`

```mdx
# Note Quality Bar

## Correct enough
## Structured
## Linked
## Useful
## Honest
## Maintainable

## Promotion rule

### Draft — incomplete or partially linked
### Active — useful and mostly linked, still changing
### Evergreen — stable, linked, reviewed, reusable
### Archived — kept for history only
```

---

## 6. Appendices

### `content-src/docs/appendices/templates/index.meta.json`

```json
{
  "title": "Templates",
  "description": "Authoring templates for body-only MDX and page-sidecar metadata.",
  "id": "REF-TPL-0001",
  "type": "reference",
  "domain": "templates",
  "status": "evergreen",
  "tags": ["reference/templates"],
  "review_cycle": "yearly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

The body of `templates.mdx` contains the full body + sidecar template pairs
for all nine note types. See `1_implementation.md` sections 4 and 5 for the
canonical templates. The `templates.mdx` body should render those templates
as reference documentation inside the site itself.

---

## 7. Section index pairs

Every top-level section and subfolder needs an `index.mdx` + `index.meta.json`
pair acting as a map note for that section.

### `content-src/docs/concepts/index.meta.json`

```json
{
  "title": "Concepts",
  "description": "Atomic ideas and theory notes.",
  "id": "MAP-CONCEPTS-0001",
  "type": "map",
  "domain": "global",
  "status": "evergreen",
  "tags": ["map/concepts"],
  "children": ["mathematics", "statistics", "information-retrieval", "representation-learning", "machine-learning", "biomedical"],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/concepts/index.mdx`

```mdx
# Concepts

## Domains

- [Mathematics](/docs/concepts/mathematics)
- [Statistics](/docs/concepts/statistics)
- [Information Retrieval](/docs/concepts/information-retrieval)
- [Representation Learning](/docs/concepts/representation-learning)
- [Machine Learning](/docs/concepts/machine-learning)
- [Biomedical](/docs/concepts/biomedical)
```

### `content-src/docs/concepts/information-retrieval/index.meta.json`

```json
{
  "title": "Information Retrieval",
  "description": "Core retrieval concepts, similarity ideas, and ranking primitives.",
  "id": "MAP-IR-0001",
  "type": "map",
  "domain": "information_retrieval",
  "status": "evergreen",
  "tags": ["map/ir"],
  "children": ["cosine-similarity", "dot-product", "vector-similarity"],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": ["Need ANN tradeoffs bridge note."]
}
```

### `content-src/docs/concepts/information-retrieval/index.mdx`

````mdx
## What this map is

This map groups the core similarity and retrieval concepts used across vector search, ranking, and matching.

## Why this matters

Retrieval behavior is downstream of the similarity assumptions you choose.

## Where this fits

- Parent: [[Domain_Map]]
- Related maps: [[Method_Map]], [[System_Map]]

## Structure

```text
Information Retrieval
├── [[cosine_similarity]]
├── [[dot_product]]
└── [[vector_similarity]]
````

## What this map helps answer

* Which similarity concepts exist in Stack Record?
* Which concepts are prerequisites for dense retrieval?
* Which notes need bridging before ANN design is fully covered?

## Notes in this map

* [[cosine_similarity]]
* [[dot_product]]
* [[vector_similarity]]

## Gaps and open loops

* ANN tradeoffs bridge note is missing
* Euclidean distance comparison note is missing

## Review

* Next review target: add comparison notes

````

### `content-src/docs/methods/index.meta.json`

```json
{
  "title": "Methods",
  "description": "Repeatable procedures and processing patterns.",
  "id": "MAP-METHODS-0001",
  "type": "map",
  "domain": "global",
  "status": "evergreen",
  "tags": ["map/methods"],
  "children": ["retrieval"],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/methods/index.mdx`

```mdx
# Methods

## Domains

- [Extraction](/docs/methods/extraction)
- [Retrieval](/docs/methods/retrieval)
- [Evaluation](/docs/methods/evaluation)
- [Reproducibility](/docs/methods/reproducibility)
- [Build](/docs/methods/build)
```

### `content-src/docs/methods/retrieval/index.meta.json`

```json
{
  "title": "Retrieval Methods",
  "description": "Methods for ranking, combining, and thresholding candidates.",
  "id": "MAP-MRET-0001",
  "type": "map",
  "domain": "retrieval",
  "status": "evergreen",
  "tags": ["map/retrieval"],
  "children": ["rrf-pipeline"],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": ["Need a thresholding note linked beneath rank fusion."]
}
```

### `content-src/docs/methods/retrieval/index.mdx`

````mdx
## What this map is

This map groups the methods used to retrieve, combine, and rank candidates.

## Why this matters

Good concepts are not enough. Retrieval quality depends on method design.

## Where this fits

- Parent: [[Method_Map]]
- Related maps: [[Domain_Map]], [[System_Map]]

## Structure

```text
Retrieval Methods
└── [[rrf_pipeline]]
````

## What this map helps answer

* Which methods combine multiple judges?
* Which methods depend on score comparability?
* Which methods are implemented in systems notes?

## Notes in this map

* [[rrf_pipeline]]

## Gaps and open loops

* threshold selection note missing
* candidate generation vs reranking note missing

## Review

* Next review target: add thresholding chain

````

### `content-src/docs/systems/index.meta.json`

```json
{
  "title": "Systems",
  "description": "Concrete implementations, architecture notes, and operational components.",
  "id": "MAP-SYSTEMS-0001",
  "type": "map",
  "domain": "global",
  "status": "evergreen",
  "tags": ["map/systems"],
  "children": ["compute"],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/systems/index.mdx`

```mdx
# Systems

## Domains

- [Pipeline](/docs/systems/pipeline)
- [Data](/docs/systems/data)
- [Compute](/docs/systems/compute)
- [Runtime](/docs/systems/runtime)
- [Security](/docs/systems/security)
```

### `content-src/docs/systems/compute/index.meta.json`

```json
{
  "title": "Compute Systems",
  "description": "Queueing, workers, orchestration, and throughput components.",
  "id": "MAP-COMPUTE-0001",
  "type": "map",
  "domain": "compute",
  "status": "evergreen",
  "tags": ["map/compute"],
  "children": ["rabbitmq-central-broker"],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": ["Need dead-letter and retry architecture notes."]
}
```

### `content-src/docs/systems/compute/index.mdx`

````mdx
## What this map is

This map groups the concrete compute-layer systems used to run and coordinate workloads.

## Why this matters

Method design only becomes operational once it is implemented in systems that move real work.

## Where this fits

- Parent: [[System_Map]]
- Related maps: [[Method_Map]], [[Domain_Map]]

## Structure

```text
Compute Systems
└── [[rabbitmq_central_broker]]
````

## What this map helps answer

* Which systems distribute jobs?
* Which systems create silent failure risks?
* Which components need monitoring?

## Notes in this map

* [[rabbitmq_central_broker]]

## Gaps and open loops

* retry policy note missing
* dead-letter queue note missing

## Review

* Next review target: add failure-handling notes

````

### `content-src/docs/maps/index.meta.json`

```json
{
  "title": "Maps",
  "description": "Top-level navigation and synthesis notes.",
  "id": "MAP-ROOT-0001",
  "type": "map",
  "domain": "global",
  "status": "evergreen",
  "tags": ["map/root"],
  "children": ["learning-map", "domain-map", "method-map", "system-map", "open-loops"],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/maps/index.mdx`

```mdx
# Maps

- [Learning Map](/docs/maps/learning-map)
- [Domain Map](/docs/maps/domain-map)
- [Method Map](/docs/maps/method-map)
- [System Map](/docs/maps/system-map)
- [Open Loops](/docs/maps/open-loops)
```

### `content-src/docs/standards/index.meta.json`

```json
{
  "title": "Standards",
  "description": "Rules for metadata, structure, closure, and note quality.",
  "id": "MAP-STANDARDS-0001",
  "type": "map",
  "domain": "standards",
  "status": "evergreen",
  "tags": ["map/standards"],
  "children": ["closure-rule", "metadata-schema", "writing-style", "note-quality-bar"],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/standards/index.mdx`

```mdx
# Standards

- [Closure Rule](/docs/standards/closure-rule)
- [Metadata Schema](/docs/standards/metadata-schema)
- [Writing Style](/docs/standards/writing-style)
- [Note Quality Bar](/docs/standards/note-quality-bar)
```

### `content-src/docs/projects/index.meta.json`

```json
{
  "title": "Projects",
  "description": "Project-level synthesis notes.",
  "id": "MAP-PROJECTS-0001",
  "type": "map",
  "domain": "project",
  "status": "evergreen",
  "tags": ["map/projects"],
  "children": ["ukb-pipeline"],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/projects/index.mdx`

```mdx
# Projects

Projects will appear here as you add them.
```

---

## 8. Additional concept page pairs

### `content-src/docs/concepts/information-retrieval/dot-product/index.meta.json`

```json
{
  "title": "Dot Product",
  "description": "A vector operation combining magnitude and alignment.",
  "id": "C-MATH-0002",
  "type": "concept",
  "domain": "information_retrieval",
  "status": "evergreen",
  "tags": ["concept/ir", "concept/maths"],
  "aliases": ["inner product"],
  "parent_maps": ["MOC_Similarity_Metrics"],
  "prerequisites": ["vectors", "magnitude"],
  "children": ["cosine-similarity"],
  "related_notes": ["vector-similarity"],
  "related_methods": ["dense_retrieval"],
  "related_systems": ["faiss_setup"],
  "related_projects": [],
  "review_cycle": "monthly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": ["When does raw vector norm contain useful semantic or confidence information?"]
}
```

### `content-src/docs/concepts/information-retrieval/dot-product/index.mdx`

````mdx
## What this is

The dot product combines pairwise coordinate multiplication and summation to produce a scalar score.

## Why this matters

It is the base operation beneath cosine similarity and many vector retrieval systems.

## Where this fits

- Parent map: [[MOC_Similarity_Metrics]]
- Prerequisites: [[vectors]], [[magnitude]]
- Used in method: [[dense_retrieval]]
- Used in system: [[faiss_setup]]
- Used in project: your project here

## Core idea

The dot product grows when vectors point in similar directions and when their magnitudes are large.

## Equation

$$
\mathbf{a}\cdot\mathbf{b} = \sum_{i=1}^{n} a_i b_i
$$

## Breakdown

### Terms

- $a_i$ = component of vector `a`
- $b_i$ = component of vector `b`

### What the equation is really doing

It multiplies aligned components and adds them, blending direction and magnitude into one score.

## Plain-English explanation

Dot product asks: "How much do these vectors point together, and how large are they while doing it?"

## Worked example

For `a = [1, 2]` and `b = [3, 4]`:

$$
1 \cdot 3 + 2 \cdot 4 = 11
$$

## ASCII diagram

```text
a ---->
b ------>

same general direction + non-zero size = positive dot product
````

## Why this is used

It is fast, fundamental, and directly supported in many vector indexes.

## Benefits

* simple
* computationally efficient
* preserves magnitude information

## Drawbacks and failure modes

* sensitive to vector norm
* hard to compare across unnormalized spaces
* can over-reward large norms

## Where I have used it

* [[faiss_setup]] — inner-product search
* Your project — vector comparison reasoning

## Questions this note answers

* What is the dot product?
* How is it different from cosine?
* Why does norm matter?

## Related notes

* [[vectors]]
* [[cosine_similarity]]
* [[vector_similarity]]

## Open questions

* When should norm be preserved instead of normalized away?

## Review

* Next review target: add rank behavior examples

````

### `content-src/docs/concepts/information-retrieval/vector-similarity/index.meta.json`

```json
{
  "title": "Vector Similarity",
  "description": "The broader family of ways to compare vectors in embedding and retrieval systems.",
  "id": "C-IR-0003",
  "type": "concept",
  "domain": "information_retrieval",
  "status": "evergreen",
  "tags": ["concept/ir"],
  "aliases": ["embedding similarity"],
  "parent_maps": ["MOC_Similarity_Metrics"],
  "prerequisites": ["vectors", "distance_metrics"],
  "children": ["cosine-similarity", "dot-product"],
  "related_notes": ["dense_retrieval"],
  "related_methods": ["dense_retrieval"],
  "related_systems": ["faiss_setup"],
  "related_projects": [],
  "review_cycle": "monthly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": ["Which metrics behave best under biomedical embedding distributions?"]
}
```

### `content-src/docs/concepts/information-retrieval/vector-similarity/index.mdx`

````mdx
## What this is

Vector similarity is the family of methods used to compare vector representations numerically.

## Why this matters

Embedding systems only become useful when you can compare vectors in a way that reflects the meaning you care about.

## Where this fits

- Parent map: [[MOC_Similarity_Metrics]]
- Prerequisites: [[vectors]], [[distance_metrics]]
- Used in method: [[dense_retrieval]]
- Used in system: [[faiss_setup]]
- Used in project: your project here

## Core idea

Different metrics define "closeness" differently. That changes ranking and retrieval behavior.

## Equation or formal logic

$$
\text{similarity}(\mathbf{a}, \mathbf{b}) \in \{\text{cosine}, \text{dot}, \text{L2-based transforms}, \dots\}
$$

## Plain-English explanation

Vector similarity is the rulebook for deciding whether two embeddings should count as "close."

## Worked example

The same two vectors can rank differently under cosine and dot product if their magnitudes differ.

## ASCII diagram

```text
vector A  ---->
vector B  --->
vector C  -------->

A vs B may be similar by direction
A vs C may dominate by norm under dot product
````

## Why this is used

It is the conceptual bridge between embeddings and retrieval.

## Benefits

* makes metric choice explicit
* prevents blind use of cosine everywhere
* clarifies why retrieval rankings change

## Drawbacks and failure modes

* easy to treat as a generic black box
* metric choice is often under-documented
* preprocessing can silently redefine similarity

## Where I have used it

* Your project — metric reasoning for retrieval design
* [[faiss_setup]] — implementation choice discussion

## Questions this note answers

* What is vector similarity?
* Why are there multiple metrics?
* Why does metric choice change retrieval behavior?

## Related notes

* [[cosine_similarity]]
* [[dot_product]]
* [[dense_retrieval]]

## Open questions

* Need a dedicated comparison note for cosine vs dot vs euclidean.

## Review

* Next review target: add ANN indexing implications

````

---

## 9. Map page pairs

### `content-src/docs/maps/learning-map/index.meta.json`

```json
{
  "title": "Learning Map",
  "description": "Entry point for the overall learning structure.",
  "id": "MAP-LEARN-0001",
  "type": "map",
  "domain": "global",
  "status": "evergreen",
  "tags": ["map/learning"],
  "children": ["domain-map", "method-map", "system-map", "open-loops"],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/maps/learning-map/index.mdx`

````mdx
## What this map is

The top-level map for how Stack Record is organized and how knowledge moves from ideas to implementation.

## Why this matters

The learning system is not just a folder tree. It is a graph connecting concepts, methods, systems, projects, and review loops.

## Where this fits

- Parent: your project
- Related maps: [[Domain_Map]], [[Method_Map]], [[System_Map]]

## Structure

```text
Learning
├── [[Domain_Map]]
├── [[Method_Map]]
├── [[System_Map]]
└── [[Open_Loops]]
````

## What this map helps answer

* Where should a new note go?
* How does a concept connect to implementation?
* Which areas are incomplete?

## Notes in this map

* [[Domain_Map]]
* [[Method_Map]]
* [[System_Map]]
* [[Open_Loops]]

## Gaps and open loops

* More domain maps need to be added
* Review automation layer not yet built

## Review

* Next review target: expand domain coverage

````

### `content-src/docs/maps/domain-map/index.meta.json`

```json
{
  "title": "Domain Map",
  "description": "Top-level domain map for concepts.",
  "id": "MAP-DOMAIN-0001",
  "type": "map",
  "domain": "global",
  "status": "evergreen",
  "tags": ["map/domain"],
  "children": ["concepts"],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/maps/domain-map/index.mdx`

````mdx
## What this map is

The domain map groups the major knowledge areas inside Stack Record.

## Why this matters

It provides the broad conceptual layer above individual atomic notes.

## Where this fits

- Parent: [[Learning_Map]]
- Related maps: [[Method_Map]], [[System_Map]]

## Structure

```text
Domains
└── [[Concepts]]
````

## What this map helps answer

* What major domains exist?
* Where should a new concept note belong?
* Which areas are thin or missing?

## Notes in this map

* [[Concepts]]

## Gaps and open loops

* statistics map missing
* biomedical map missing

## Review

* Next review target: add more domain branches

````

### `content-src/docs/maps/method-map/index.meta.json`

```json
{
  "title": "Method Map",
  "description": "Top-level map for procedural notes.",
  "id": "MAP-METHOD-0001",
  "type": "map",
  "domain": "global",
  "status": "evergreen",
  "tags": ["map/method"],
  "children": ["methods"],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/maps/method-map/index.mdx`

````mdx
## What this map is

The method map groups the repeatable procedures used across projects.

## Why this matters

Methods operationalize concepts into concrete steps.

## Where this fits

- Parent: [[Learning_Map]]
- Related maps: [[Domain_Map]], [[System_Map]]

## Structure

```text
Methods
└── [[Methods]]
````

## What this map helps answer

* Which methods exist?
* Which methods depend on which concepts?
* Which methods still need implementation notes?

## Notes in this map

* [[Methods]]

## Gaps and open loops

* evaluation methods missing
* extraction methods missing

## Review

* Next review target: add non-retrieval methods

````

### `content-src/docs/maps/system-map/index.meta.json`

```json
{
  "title": "System Map",
  "description": "Top-level map for implementation and architecture notes.",
  "id": "MAP-SYSTEM-0001",
  "type": "map",
  "domain": "global",
  "status": "evergreen",
  "tags": ["map/system"],
  "children": ["systems"],
  "review_cycle": "quarterly",
  "last_reviewed": "2026-04-14",
  "closure_score": 6,
  "closure_status": "closed",
  "open_questions": []
}
```

### `content-src/docs/maps/system-map/index.mdx`

````mdx
## What this map is

The system map groups concrete architecture and implementation notes.

## Why this matters

Methods do not run themselves. They require systems.

## Where this fits

- Parent: [[Learning_Map]]
- Related maps: [[Domain_Map]], [[Method_Map]]

## Structure

```text
Systems
└── [[Systems]]
````

## What this map helps answer

* Which implementation notes exist?
* Which systems support which methods?
* Which operational components are missing?

## Notes in this map

* [[Systems]]

## Gaps and open loops

* security notes missing
* runtime monitoring notes missing

## Review

* Next review target: extend compute and runtime branches

````

---

## 10. Full closure-rule body

### `content-src/docs/standards/closure-rule/index.mdx`

```mdx
# Closure Rule

A note is not complete because it exists. A note is complete only when it is **closed** across the knowledge graph.

## The closure dimensions

Each note is scored across six dimensions.

### U — Upward closure

The note links to at least one parent map or organizing frame.

### L — Lateral closure

The note links to at least two related peer notes.

### D — Downward closure

The note links to at least one more specific note, example, comparison, implementation, or child concept.

### A — Applied closure

The note links to at least one real use: project, implementation, system, experiment, or practical use case.

### E — Epistemic closure

The note states: what is known, limitations or failure modes, uncertainty or open questions.

### M — Maintenance closure

The note includes: status, review cycle, last reviewed, next revision target or open loop.

## Closure score

Closure Score = U + L + D + A + E + M. Each dimension is binary (0 or 1).

## Interpretation

* 6/6 = closed
* 4/6 or 5/6 = usable but incomplete
* 0/6 to 3/6 = orphan or draft

## By note type

### Concept note closure

One parent map, two related/prerequisite concepts, one child/example/comparison, one related method, one related system or project, drawbacks or failure modes, open questions, review metadata.

### Method note closure

One parent map, concept dependencies, implementation link, evaluation/validation link, inputs and outputs, benefits and drawbacks, failure modes, where used, review metadata.

### System note closure

One parent map, implemented method link, dependency links, architecture block, configuration contract, failure modes, monitoring section, where used, review metadata.

### Decision note closure

Context, options considered, why chosen, tradeoffs, consequences, review trigger.

### Experiment note closure

Question, hypothesis, setup, procedure, results, interpretation, threats to validity, feedback links to affected notes.

## Rule of use

No note should be promoted to evergreen unless it reaches at least 5/6.
```