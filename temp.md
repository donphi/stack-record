---
name: Folder-per-article restructure
overview: Restructure leaf articles from flat `slug.mdx` + `slug.meta.json` pairs to `slug/index.mdx` + `slug/index.meta.json` inside per-article folders, updating all meta.json nav files, the materialiser, kg-builder, Obsidian scripts, and documentation to match.
todos:
  - id: move-articles
    content: Move all 21 flat article pairs into per-article folders (slug/index.mdx + slug/index.meta.json)
    status: pending
  - id: move-data-json
    content: Move library-registry.data.json into library-registry/ folder and update 3 path references (schema.yaml, library-table.tsx, docker-compose.yml)
    status: pending
  - id: template-symlinks
    content: Create _template symlinks in subfolders that contain articles
    status: pending
  - id: update-obsidian-script
    content: Update create-note-pair.js to create slug/ folder with index.mdx + index.meta.json
    status: pending
  - id: update-obsidian-readme
    content: Update obsidian/README.md file path examples for folder-per-article structure
    status: pending
  - id: update-plan-docs
    content: Update 0_overview.md and 1_implementation.md authoring tree diagrams
    status: pending
  - id: update-llm-guide
    content: Update llm-writing-guide.mdx path examples if any
    status: pending
  - id: verify-build
    content: Run pnpm docs:materialize and KG builder to verify no breakage
    status: pending
isProject: false
---

# Folder-Per-Article Restructure

## Problem

Currently, leaf articles live as flat siblings in their parent folder:

```
concepts/information-retrieval/
  meta.json
  index.mdx + index.meta.json         (section hub)
  cosine-similarity.mdx                (article)
  cosine-similarity.meta.json          (article sidecar)
  dot-product.mdx
  dot-product.meta.json
```

This creates a messy mix of files at the same level. The same issue affects `maps/`, `standards/`, `appendices/`, `methods/retrieval/`, and `systems/compute/`.

## Target structure

Each leaf article gets its own folder. The folder name is the slug. Inside: `index.mdx` + `index.meta.json`.

```
concepts/information-retrieval/
  meta.json                            (unchanged)
  index.mdx + index.meta.json         (section hub, unchanged)
  cosine-similarity/
    index.mdx + index.meta.json       (article, moved + renamed)
  dot-product/
    index.mdx + index.meta.json
  vector-similarity/
    index.mdx + index.meta.json
```

## Fumadocs compatibility: confirmed

Per [Fumadocs page conventions](https://fumadocs.dev/docs/headless/page-conventions):

- `./dir/page.mdx` generates slug `['dir', 'page']`
- `./dir/index.mdx` generates slug `['dir']`
- A folder containing `index.mdx` acts as a "folder page" in the sidebar

**Crucially**, the `meta.json` `pages` array references work identically for both flat files and folders:
- `"cosine-similarity"` in `pages` resolves to **either** `cosine-similarity.mdx` (flat) or `cosine-similarity/index.mdx` (folder) -- same slug either way.

Therefore: **no changes needed to any `meta.json` `pages` arrays**. The sidebar navigation works unchanged.

## Impact analysis: what changes

### Files that need NO changes

- **`meta.json` files** (all 36) -- `pages` arrays reference slugs, which are unchanged
- **`source.config.ts`** -- reads `.generated/docs/`, unaffected
- **`lib/source.ts`** -- loader/icon resolver, unaffected
- **`app/docs/` layout and page** -- standard Fumadocs routing, slug-based
- **`lib/note-types.ts`** -- type definitions only
- **`lib/closure.ts`** -- scoring logic only
- **`tools/lib-registry/`** -- no content tree walking
- **`tools/kg-extractor/`** -- reads SQLite only
- **Docker compose mounts** -- directory-level, unaffected

### Files that MUST be updated

1. **Content files** -- move every flat leaf article pair into a folder:
   - `slug.mdx` -> `slug/index.mdx`
   - `slug.meta.json` -> `slug/index.meta.json`
   - Affected sections: `concepts/information-retrieval/` (3 articles), `methods/retrieval/` (1), `systems/compute/` (1), `maps/` (6 articles), `standards/` (4 articles), `appendices/` (5 articles + 1 data file), `notes/` (1 article)

2. **[scripts/materialize-fumadocs.ts](scripts/materialize-fumadocs.ts)** -- the pairing logic at line ~102 derives the sidecar path by replacing `.mdx` extension with `.meta.json`. This **already works** for `slug/index.mdx` -> `slug/index.meta.json`. The `slugFromMetaPath` function (line ~114) also **already handles** the `/index` case. **No code changes needed** -- the materialiser is already compatible.

3. **[tools/kg-builder/scripts/build_kg.py](tools/kg-builder/scripts/build_kg.py)** -- the `slug_from_meta_path` and `slug_from_mdx_path` functions (lines ~73-91) **already handle** the `/index` case. **No code changes needed**.

4. **[obsidian/scripts/create-note-pair.js](obsidian/scripts/create-note-pair.js)** -- **MUST be updated**. Currently creates flat files (line 61-62):
   ```javascript
   const mdxPath  = `${targetDir}/${slug}.mdx`;
   const jsonPath = `${targetDir}/${slug}.meta.json`;
   ```
   Must change to:
   ```javascript
   const mdxPath  = `${targetDir}/${slug}/index.mdx`;
   const jsonPath = `${targetDir}/${slug}/index.meta.json`;
   ```
   Also needs to `createFolder` for the slug directory.

5. **[obsidian/README.md](obsidian/README.md)** -- update the "Creating a new note" section (line ~104-107) that shows the flat file output example; update to show folder-per-article output.

6. **`_template` folders** -- currently at `concepts/_template/`, `methods/_template/`, etc. (9 locations). These stay at their current location (top-level within each section). The plan in `temp.md` suggests symlinks into each subfolder for easy access from Obsidian. This is a good idea: create symlinks like `concepts/information-retrieval/_template -> ../_template` so the writer always sees the template nearby. These symlinks are lightweight and cause no issues.

7. **Special case: `appendices/library-registry.data.json`** -- this data file sits at `appendices/library-registry.data.json` and is referenced by:
   - [tools/kg-builder/config/schema.yaml](tools/kg-builder/config/schema.yaml) (`paths.library_registry_json`)
   - [components/library-table.tsx](components/library-table.tsx) (static import)
   - [tools/lib-registry/docker-compose.yml](tools/lib-registry/docker-compose.yml) (mount)
   
   If `library-registry.mdx` moves to `library-registry/index.mdx`, the `.data.json` should move into the folder too: `library-registry/library-registry.data.json` (or stay where it is, since it's not an `.mdx`/`.meta.json` pair but a data dependency). **Recommended: move it into the folder** as `library-registry/library-registry.data.json` and update the 3 references above.

8. **[0_overview.md](0_overview.md)** and **[1_implementation.md](1_implementation.md)** -- update the authoring tree diagrams to show folder-per-article structure.

9. **[content-src/docs/appendices/llm-writing-guide.mdx](content-src/docs/appendices/llm-writing-guide.mdx)** and **[temp.md](temp.md)** -- any file path examples in the LLM writing guide or obsidian plan that show flat file pairs should be updated.

## Obsidian compatibility: works well

The folder-per-article structure is **friendlier** for Obsidian than flat files:

- Each article is a clean folder in the sidebar, expandable to show its `index.mdx` and `index.meta.json`
- The `mdx-as-md-obsidian` plugin will still preview `index.mdx` files
- Wikilinks `[[cosine_similarity]]` still resolve (Obsidian resolves by filename, and `index.mdx` in a folder named `cosine-similarity` is still findable -- though you may want to configure the wikilink resolution)
- The Templater script creates the folder and the two files inside it
- `_template` symlinks in each subfolder give quick sidebar access

**One consideration**: Obsidian's wikilink resolution searches by filename. Multiple files named `index.mdx` could cause ambiguity. However, the Copilot/wikilink system in this repo uses underscore-based wiki keys (`[[cosine_similarity]]`), not filename-based links. The materialiser resolves these to proper URLs. So this is not an issue for the build pipeline. For Obsidian's internal link resolution, the `mdx-as-md` plugin + Copilot QA indexing should handle it, but it's worth testing.

## Complete file move list

### concepts/information-retrieval/ (3 articles)
- `cosine-similarity.mdx` + `.meta.json` -> `cosine-similarity/index.mdx` + `index.meta.json`
- `dot-product.mdx` + `.meta.json` -> `dot-product/index.mdx` + `index.meta.json`
- `vector-similarity.mdx` + `.meta.json` -> `vector-similarity/index.mdx` + `index.meta.json`

### methods/retrieval/ (1 article)
- `rrf-pipeline.mdx` + `.meta.json` -> `rrf-pipeline/index.mdx` + `index.meta.json`

### systems/compute/ (1 article)
- `rabbitmq-central-broker.mdx` + `.meta.json` -> `rabbitmq-central-broker/index.mdx` + `index.meta.json`

### maps/ (6 articles)
- `domain-map.mdx` + `.meta.json` -> `domain-map/index.mdx` + `index.meta.json`
- `learning-map.mdx` + `.meta.json` -> `learning-map/index.mdx` + `index.meta.json`
- `method-map.mdx` + `.meta.json` -> `method-map/index.mdx` + `index.meta.json`
- `system-map.mdx` + `.meta.json` -> `system-map/index.mdx` + `index.meta.json`
- `open-loops.mdx` + `.meta.json` -> `open-loops/index.mdx` + `index.meta.json`
- `toc-test.mdx` + `.meta.json` -> `toc-test/index.mdx` + `index.meta.json`

### standards/ (4 articles)
- `closure-rule.mdx` + `.meta.json` -> `closure-rule/index.mdx` + `index.meta.json`
- `metadata-schema.mdx` + `.meta.json` -> `metadata-schema/index.mdx` + `index.meta.json`
- `writing-style.mdx` + `.meta.json` -> `writing-style/index.mdx` + `index.meta.json`
- `note-quality-bar.mdx` + `.meta.json` -> `note-quality-bar/index.mdx` + `index.meta.json`

### appendices/ (5 articles + 1 data file)
- `glossary.mdx` + `.meta.json` -> `glossary/index.mdx` + `index.meta.json`
- `notation.mdx` + `.meta.json` -> `notation/index.mdx` + `index.meta.json`
- `templates.mdx` + `.meta.json` -> `templates/index.mdx` + `index.meta.json`
- `library-registry.mdx` + `.meta.json` -> `library-registry/index.mdx` + `index.meta.json`
- `library-registry.data.json` -> `library-registry/library-registry.data.json`
- `llm-writing-guide.mdx` + `.meta.json` -> `llm-writing-guide/index.mdx` + `index.meta.json`

### notes/ (1 article)
- `ideas.mdx` + `.meta.json` -> `ideas/index.mdx` + `index.meta.json`

## Template symlinks

Create symlinks in each subfolder that has articles, pointing back to the section-level `_template`:

```bash
# Example for concepts/information-retrieval/
cd content-src/docs/concepts/information-retrieval
ln -s ../_template _template
```

Repeat for every subfolder that contains articles. This keeps `_template` accessible in Obsidian's sidebar without duplicating files.

## Obsidian plan (temp.md) impact

The Obsidian plan in `temp.md` is **compatible** with this restructure. The only updates needed:

- The `create-note-pair.js` script (already noted above) must output `slug/index.mdx` instead of `slug.mdx`
- The README examples showing file paths must use the folder-per-article pattern
- The `_template` symlink approach mentioned in `temp.md` aligns perfectly with this restructure

## Sidebar behavior

The Fumadocs sidebar will render identically. `meta.json` `pages` arrays like `["cosine-similarity", "dot-product", "vector-similarity"]` resolve to folders with `index.mdx` the same way they resolve to flat files. The page tree structure is unchanged. No sidebar breakage.

## Implementation order

1. Move all flat article pairs into folders (git mv for clean history)
2. Move `library-registry.data.json` into the `library-registry/` folder
3. Update the 3 references to `library-registry.data.json` path
4. Create `_template` symlinks in subfolders
5. Update `obsidian/scripts/create-note-pair.js` for folder creation
6. Update `obsidian/README.md` examples
7. Update `0_overview.md` and `1_implementation.md` diagrams
8. Update `llm-writing-guide.mdx` if it contains path examples
9. Run `pnpm docs:materialize` to verify the build passes
10. Run the KG builder to verify no slug changes
