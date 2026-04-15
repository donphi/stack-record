# kg-builder

Build a SQLite knowledge graph from Stack Record content metadata, MDX bodies,
and the library registry.

## How it works

```
content-src/docs/          config/schema.yaml
  *.meta.json  (sidecars)       (field mappings,
  meta.json    (nav trees)       edge tables,
  *.mdx        (bodies)          feature toggles)
  library-registry.data.json         |
        |                            |
        v                            v
    Python script (build_kg.py)
        |
        v
  data/kg.sqlite3            output/knowledge_graph.jsonld
  (fully-linked graph)       (optional JSON-LD export)
```

The output SQLite database has:
- **Notes** — one row per page sidecar, with all scalar metadata
- **Edge tables** — one junction table per relationship type (parent_maps,
  children, related_methods, uses_concepts, etc.) enabling multi-hop chain
  traversal
- **Body sections** — each `##` heading becomes a sub-node with its text
- **Wiki links** — `[[...]]` links from MDX bodies, parallel to sidecar edges
- **Folders** — navigation hierarchy from `meta.json` files
- **Libraries** — full registry with sections, alternatives, and note links
- **key_to_note** — lookup table for resolving wiki-style keys to note IDs

## Quickstart

```bash
# 1. Review/edit config/schema.yaml (controls everything)

# 2. Run
docker compose run --rm kg-builder

# 3. Output
sqlite3 data/kg.sqlite3 ".tables"
```

## Maximum control principle

**`config/schema.yaml` is the single control surface.** Every feature can be
toggled on/off or pruned directly in this file. No code changes required.

- Remove entries from `array_edge_tables` to skip specific edge types
- Set `wiki_link_extraction.enabled: false` to skip body wiki-link extraction
- Set `body_section_extraction.enabled: false` to skip body section splitting
- Set `library_registry.enabled: false` to skip library ingestion
- Set `jsonld.enabled: false` to skip JSON-LD export
- Delete any individual edge entry (e.g. `note_deciders`) and that table
  simply won't be created or populated

## Project structure

```
kg-builder/
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
├── README.md
├── config/
│   └── schema.yaml         # THE config — all parameters live here
├── scripts/
│   ├── build_kg.py          # Main pipeline script
│   └── db_schema.py         # Idempotent SQLite table creation
├── data/
│   └── (kg.sqlite3)         # Generated output
└── output/
    └── (knowledge_graph.jsonld)  # Optional JSON-LD export
```

## What you edit

**Only `config/schema.yaml`.** This file defines:

- `paths` — where to find content and where to write output
- `note_fields` — which sidecar fields are required, which are scalar columns
- `array_edge_tables` — which array fields become junction tables (and what style)
- `wiki_link_extraction` / `body_section_extraction` — MDX body processing toggles
- `library_registry` — library ingestion toggle and field list
- `jsonld` — JSON-LD export toggle and namespace config

## Chain traversal examples

The normalized schema enables long multi-hop chains. Every relationship type
is its own table, joined through `key_to_note` for resolution.

**5-hop chain (concept → map → sibling → method → implementation):**

```sql
SELECT c.title AS concept, m.title AS map, child.title AS sibling,
       method_note.title AS method, impl.title AS implementation
FROM notes c
JOIN note_parent_maps pm ON pm.note_id = c.id
JOIN key_to_note k1 ON k1.key = pm.target_key
JOIN notes m ON m.id = k1.note_id
JOIN note_children mc ON mc.note_id = m.id
JOIN key_to_note k2 ON k2.key = mc.target_key
JOIN notes child ON child.id = k2.note_id
JOIN note_related_methods rm ON rm.note_id = child.id
JOIN key_to_note k3 ON k3.key = rm.target_key
JOIN notes method_note ON method_note.id = k3.note_id
JOIN note_implemented_in ni ON ni.note_id = method_note.id
JOIN key_to_note k4 ON k4.key = ni.target_key
JOIN notes impl ON impl.id = k4.note_id
WHERE c.id = 'C-IR-0007';
```

**Cross-domain chain (project → system → library → alternative → section):**

```sql
SELECT p.title AS project, sys.title AS system_note,
       l.name AS library, la.alternative AS alt_library,
       ls.title AS pipeline_section
FROM notes p
JOIN note_key_systems ks ON ks.note_id = p.id
JOIN key_to_note k1 ON k1.key = ks.target_key
JOIN notes sys ON sys.id = k1.note_id
JOIN library_note_links ln ON ln.note_id = sys.id
JOIN libraries l ON l.number = ln.library_number
JOIN lib_alternatives la ON la.library_number = l.number
JOIN lib_sections ls ON ls.id = l.section_id
WHERE p.type = 'project';
```

**Body section search (find all notes with "Failure modes" content):**

```sql
SELECT n.title, ns.body
FROM note_sections ns
JOIN notes n ON n.id = ns.note_id
WHERE ns.heading = 'Failure modes'
  AND ns.body != '';
```

**Wiki-link gap analysis (body links not in any sidecar edge):**

```sql
SELECT wl.source_slug, wl.target_raw, wl.target_key,
       CASE WHEN ktn.note_id IS NOT NULL THEN 'resolved' ELSE 'unresolved' END AS status
FROM wiki_links wl
LEFT JOIN key_to_note ktn ON ktn.key = wl.target_key
ORDER BY status, wl.source_slug;
```
