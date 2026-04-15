# KG Extractor

Extract a standards-compliant JSON-LD knowledge graph from any SQLite database.

## How it works

```
SQLite (.db)  +  config/schema.yaml  →  Python script  →  knowledge_graph.jsonld
(your data)      (your table mapping)                      (portable output)
```

The JSON-LD output is simultaneously:
- **Valid JSON** — any tool, any language can parse it
- **Valid RDF** — any triple store (Jena, GraphDB) can ingest it
- **Neo4j-ready** — load via Neosemantics (n10s) plugin
- **RAG-ready** — each `@graph` entry is a natural chunk

## Quickstart

```bash
# 1. Put your SQLite database in ./data/
cp /path/to/your/wiki.db ./data/

# 2. Edit config/schema.yaml to match your actual tables
#    (replace the example tables/columns with yours)

# 3. Run
docker compose run --rm extractor

# 4. Output
cat output/knowledge_graph.jsonld
```

## Targeting a different database file

```bash
DB_FILE=my_other.db docker compose run --rm extractor
```

## Project structure

```
kg-extractor/
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
├── README.md
├── scripts/
│   └── extract.py          # The extractor — reads SQLite + YAML, writes JSON-LD
├── config/
│   └── schema.yaml         # YOUR config — map tables → RDF types & predicates
├── data/
│   └── (your .db file)     # Mounted read-only into container
└── output/
    └── knowledge_graph.jsonld  # Generated output
```

## What you edit

**Only `config/schema.yaml`.** This file defines:

- `base_uri` — your namespace (e.g. `http://mywiki.local/kg/`)
- `namespaces` — RDF prefix mappings (schema.org, Dublin Core, custom)
- `node_types` — which SQLite tables are entities, and which columns map to which RDF predicates
- `edge_types` — which SQLite tables are relationships, with subject/object foreign keys

The extractor reads this config and your database. Zero hardcoded values in the Python script.

## Output format

```json
{
  "@context": {
    "@base": "http://mywiki.local/kg/",
    "schema": "http://schema.org/",
    "dcterms": "http://purl.org/dc/terms/",
    "title": "dcterms:title",
    "name": "schema:name"
  },
  "@graph": [
    {
      "@id": "page:1",
      "@type": "wiki:WikiPage",
      "title": "Gradient Descent",
      "category": "optimization"
    },
    {
      "@id": "page:1",
      "wiki:referencesEquation": { "@id": "eq:42" }
    }
  ]
}
```

## Next steps

- **Neo4j**: install Neosemantics (n10s), then `CALL n10s.rdf.import.fetch("file:///output/knowledge_graph.jsonld", "JSON-LD")`
- **RAG**: iterate `@graph` entries, embed each node's text fields, store in vector DB
- **Training**: flatten the graph to subject-predicate-object triples for fine-tuning datasets
- **SPARQL**: load into Apache Jena Fuseki and query with SPARQL
