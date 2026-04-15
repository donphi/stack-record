# ============================================================================
# FILE: extract.py
# LOCATION: scripts/extract.py
# PIPELINE POSITION: Step 1 of 1 — single-pass extraction
# PURPOSE: Read SQLite database + YAML schema, emit standards-compliant JSON-LD
# ============================================================================
"""
MODULE OVERVIEW:
Walks every table declared in config/schema.yaml, reads rows from the
SQLite database, maps columns to RDF predicates via the YAML config,
and writes a single JSON-LD file (or one per entity type, configurable).

CLASSES:
- KnowledgeGraphExtractor: Drives the full extraction pipeline

METHODS:
- load_schema(): Parse YAML config into internal ontology map
- connect_db(): Open SQLite database
- extract_nodes(): Pull all node-type tables
- extract_edges(): Pull all relationship tables
- build_jsonld(): Assemble the JSON-LD document
- write_output(): Write to disk

HYPERPARAMETERS:
- All externalized to config/schema.yaml — zero hardcoded values here

SEEDS:
- N/A (deterministic extraction)

DEPENDENCIES:
- pyyaml==6.0.2
- rich==14.0.0
"""

import json
import sqlite3
import sys
from pathlib import Path

import yaml

# Why try/except: rich is optional — works in Docker, falls back to print locally
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ── Paths (resolved relative to project root) ────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "schema.yaml"

if RICH_AVAILABLE:
    console = Console()
else:
    class _PlainConsole:
        def print(self, msg, **kw): print(msg)
        def rule(self, msg, **kw): print(f"\n{'='*60}\n{msg}\n{'='*60}")
    console = _PlainConsole()


class KnowledgeGraphExtractor:
    """
    Reads a SQLite database and a YAML schema definition,
    then emits a standards-compliant JSON-LD knowledge graph.

    Why JSON-LD: it is simultaneously valid JSON (any tool can parse it)
    and valid RDF (any triple store can ingest it). Maximum future flexibility.
    """

    def __init__(self, db_path: str, config_path: str = str(CONFIG_PATH)):
        self.db_path = db_path
        self.config_path = config_path
        self.schema = {}
        self.conn = None
        self.graph = {"@context": {}, "@graph": []}

    # ── 1. Load YAML schema ──────────────────────────────────────────────
    def load_schema(self):
        """
        Parse config/schema.yaml into the ontology map.

        The YAML defines:
        - namespace / base_uri  → becomes @context
        - node_types            → which tables are entities, and column→predicate mapping
        - edge_types            → which tables are relationships
        """
        with open(self.config_path, "r") as f:
            self.schema = yaml.safe_load(f)

        # Build the JSON-LD @context from the YAML namespaces
        ctx = {}
        base = self.schema.get("base_uri", "http://example.org/kg/")
        ctx["@base"] = base

        for prefix, uri in self.schema.get("namespaces", {}).items():
            ctx[prefix] = uri

        # Map each property shortname → full predicate IRI
        for nt in self.schema.get("node_types", []):
            for col_def in nt.get("columns", []):
                alias = col_def.get("alias", col_def["column"])
                predicate = col_def.get("predicate")
                if predicate:
                    ctx[alias] = predicate

        self.graph["@context"] = ctx
        console.print(f"[green]✅ Schema loaded — {len(self.schema.get('node_types', []))} node types, "
                       f"{len(self.schema.get('edge_types', []))} edge types[/green]")

    # ── 2. Connect to SQLite ─────────────────────────────────────────────
    def connect_db(self):
        """Open the SQLite database in read-only mode."""
        db = Path(self.db_path)
        if not db.exists():
            console.print(f"[red]❌ Database not found: {self.db_path}[/red]")
            sys.exit(1)

        # Why uri=True + mode=ro: prevents accidental writes to source of truth
        self.conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row
        console.print(f"[green]✅ Connected to {db.name} (read-only)[/green]")

    # ── 3. Extract nodes ─────────────────────────────────────────────────
    def extract_nodes(self):
        """
        For each node_type in schema.yaml, query the SQLite table
        and convert every row into a JSON-LD node.
        """
        node_types = self.schema.get("node_types", [])

        for nt in node_types:
            table = nt["table"]
            rdf_type = nt["rdf_type"]
            id_column = nt.get("id_column", "id")
            columns = nt.get("columns", [])

            cursor = self.conn.execute(f"SELECT * FROM [{table}]")
            rows = cursor.fetchall()
            console.print(f"  Processing {table} ({len(rows)} rows)...")

            for row in rows:
                node = {
                    "@id": f"{nt.get('id_prefix', table)}:{row[id_column]}",
                    "@type": rdf_type,
                }

                for col_def in columns:
                    col_name = col_def["column"]
                    alias = col_def.get("alias", col_name)
                    value = row[col_name] if col_name in row.keys() else None

                    if value is not None:
                        node[alias] = value

                self.graph["@graph"].append(node)

        console.print(f"✅ Extracted {len(self.graph['@graph'])} nodes")

    # ── 4. Extract edges ─────────────────────────────────────────────────
    def extract_edges(self):
        """
        For each edge_type in schema.yaml, query the relationship table
        and add edges as JSON-LD nodes linking subject → object.

        Why edges-as-nodes: JSON-LD can represent relationships either inline
        or as reified statements. Reified nodes let you attach properties
        to the relationship itself (confidence, timestamp, source).
        """
        edge_types = self.schema.get("edge_types", [])
        edge_count = 0

        for et in edge_types:
            table = et["table"]
            subject_col = et["subject_column"]
            object_col = et["object_column"]
            subject_prefix = et.get("subject_prefix", "node")
            object_prefix = et.get("object_prefix", "node")
            predicate = et["predicate"]
            extra_columns = et.get("columns", [])

            cursor = self.conn.execute(f"SELECT * FROM [{table}]")
            rows = cursor.fetchall()
            console.print(f"  Processing {table} ({len(rows)} edges)...")

            for row in rows:
                subj_id = f"{subject_prefix}:{row[subject_col]}"
                obj_id = f"{object_prefix}:{row[object_col]}"

                edge_entry = {
                    "@id": subj_id,
                    predicate: {"@id": obj_id},
                }

                # Attach extra properties if the edge table has them
                for col_def in extra_columns:
                    col_name = col_def["column"]
                    alias = col_def.get("alias", col_name)
                    value = row[col_name] if col_name in row.keys() else None
                    if value is not None:
                        if isinstance(edge_entry[predicate], dict) and "@id" in edge_entry[predicate]:
                            edge_entry[predicate] = {
                                "@id": obj_id,
                                alias: value,
                            }

                self.graph["@graph"].append(edge_entry)
                edge_count += 1

        console.print(f"✅ Extracted {edge_count} edges")

    # ── 5. Build and write output ────────────────────────────────────────
    def write_output(self, output_path: str):
        """
        Write the assembled JSON-LD to disk.

        The output is a single .jsonld file that is:
        - Valid JSON (parseable by any language/tool)
        - Valid JSON-LD (ingestible by any RDF triple store)
        - Loadable into Neo4j via Neosemantics (n10s)
        - Usable as-is for RAG chunking (each @graph entry is a chunk)
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.graph, f, indent=2, ensure_ascii=False)

        size_kb = out.stat().st_size / 1024
        node_count = len(self.graph["@graph"])
        console.print(f"\n[bold green]✅ Output written: {out}[/bold green]")
        console.print(f"   Nodes + edges: {node_count}")
        console.print(f"   File size: {size_kb:.1f} KB")

    # ── Orchestrator ─────────────────────────────────────────────────────
    def run(self, output_path: str):
        """Full pipeline: load → connect → extract → write."""
        console.rule("[bold blue]Knowledge Graph Extraction[/bold blue]")
        self.load_schema()
        self.connect_db()
        self.extract_nodes()
        self.extract_edges()
        self.write_output(output_path)
        self.conn.close()
        console.rule("[bold blue]Done[/bold blue]")


# ── CLI entry point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract a JSON-LD knowledge graph from SQLite + YAML schema"
    )
    parser.add_argument(
        "--db", type=str, default="/app/data/wiki.db",
        help="Path to SQLite database"
    )
    parser.add_argument(
        "--config", type=str, default="/app/config/schema.yaml",
        help="Path to YAML schema config"
    )
    parser.add_argument(
        "--output", type=str, default="/app/output/knowledge_graph.jsonld",
        help="Output JSON-LD file path"
    )

    args = parser.parse_args()
    extractor = KnowledgeGraphExtractor(db_path=args.db, config_path=args.config)
    extractor.run(output_path=args.output)

print("✅ extract.py loaded successfully")
