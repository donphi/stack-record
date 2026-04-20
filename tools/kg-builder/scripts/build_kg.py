"""
PURPOSE: Build a SQLite knowledge graph from content-src metadata,
         MDX body files, and the library registry JSON.

OWNS:
  - Walking content-src for *.meta.json, meta.json, and *.mdx files
  - Stripping Fumadocs folder-group segments from paths (parenthesized dirs)
  - Populating all tables defined in config/schema.yaml
  - Building the key_to_note lookup for chain resolution
  - Wiki-link extraction from MDX bodies
  - Body section extraction (heading → sub-node splitting)
  - Library registry ingestion from JSON
  - Optional JSON-LD export
  - Closure validation warnings

HYPERPARAMETERS:
  - All externalized to config/schema.yaml — zero hardcoded values here

DEPENDENCIES:
  - pyyaml==6.0.2
  - rich==14.0.0
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import yaml

try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

if RICH_AVAILABLE:
    console = Console()
else:
    class _PlainConsole:
        def print(self, msg, **kw):
            print(msg)
        def rule(self, msg, **kw):
            print(f"\n{'=' * 60}\n{msg}\n{'=' * 60}")
    console = _PlainConsole()

sys.path.insert(0, os.path.dirname(__file__))
from db_schema import get_connection


# ── File classification ──────────────────────────────────────────────────

def is_page_meta(filepath: str) -> bool:
    return filepath.endswith(".meta.json") and os.path.basename(filepath) != "meta.json"


def is_folder_meta(filepath: str) -> bool:
    return os.path.basename(filepath) == "meta.json"


def is_mdx_body(filepath: str) -> bool:
    return filepath.endswith(".mdx")


def list_files_recursive(directory: str) -> list[str]:
    out = []
    for root, _dirs, files in os.walk(directory):
        for f in files:
            out.append(os.path.join(root, f))
    return out


# ── Folder-group stripping ────────────────────────────────────────────────

def strip_folder_groups(rel_path: str) -> str:
    """Remove Fumadocs folder-group segments (parenthesized dirs) from a path.

    Folder groups like ``(01-navigation)`` are transparent to Fumadocs routing
    and must not appear in slugs or folder_path values stored in the KG.
    """
    parts = rel_path.split("/")
    return "/".join(p for p in parts if not (p.startswith("(") and p.endswith(")")))


# ── Slug derivation (mirrors materialize-fumadocs.ts) ────────────────────

def slug_from_meta_path(meta_path: str, content_src: str) -> str:
    rel = os.path.relpath(meta_path, content_src).replace(os.sep, "/")
    rel = strip_folder_groups(rel)
    without_ext = re.sub(r"\.meta\.json$", "", rel)
    if without_ext.endswith("/index") or without_ext == "index":
        directory = re.sub(r"/?index$", "", without_ext)
        return directory if directory else ""
    return without_ext


def slug_from_mdx_path(mdx_path: str, content_src: str) -> str:
    rel = os.path.relpath(mdx_path, content_src).replace(os.sep, "/")
    rel = strip_folder_groups(rel)
    without_ext = re.sub(r"\.mdx$", "", rel)
    if without_ext.endswith("/index") or without_ext == "index":
        directory = re.sub(r"/?index$", "", without_ext)
        return directory if directory else ""
    return without_ext


def to_wiki_key(slug: str) -> str:
    last = slug.rsplit("/", 1)[-1] if "/" in slug else slug
    return last.replace("-", "_").lower()


def _camel_to_kebab(name: str) -> str:
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name)
    s = re.sub(r"([A-Z])([A-Z][a-z])", r"\1-\2", s)
    return s.lower()


def normalize_wiki_name(raw: str) -> str:
    has_lower = bool(re.search(r"[a-z]", raw))
    has_upper = bool(re.search(r"[A-Z]", raw))
    if has_lower and has_upper and "_" not in raw:
        return _camel_to_kebab(raw).replace("-", "_").lower()
    return raw.replace("-", "_").lower()


# ── Section splitting ────────────────────────────────────────────────────

def split_sections(body: str, heading_pattern: str) -> list[dict]:
    """Split an MDX body into sections by heading lines."""
    compiled = re.compile(heading_pattern, re.MULTILINE)
    sections = []
    matches = list(compiled.finditer(body))

    for i, match in enumerate(matches):
        level = len(match.group(1))
        heading = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_body = body[start:end].strip()
        sections.append({
            "heading": heading,
            "heading_level": level,
            "sort_order": i,
            "body": section_body,
        })

    return sections


# ── Wiki link extraction ─────────────────────────────────────────────────

def extract_wiki_links(body: str, pattern: str) -> list[dict]:
    """Extract all [[wiki links]] from an MDX body."""
    compiled = re.compile(pattern)
    links = []
    for match in compiled.finditer(body):
        raw = match.group(1)
        key = normalize_wiki_name(raw)
        links.append({"target_raw": raw, "target_key": key})
    return links


# ── Note ingestion ───────────────────────────────────────────────────────

def ingest_notes(
    conn: sqlite3.Connection,
    content_src: str,
    schema: dict,
    all_files: list[str],
) -> None:
    """Read all *.meta.json sidecars and populate the notes table + edge tables."""
    note_cfg = schema["note_fields"]
    required = note_cfg["required"]
    scalar = note_cfg["scalar"]
    valid_types = schema["valid_note_types"]
    edge_tables = schema.get("array_edge_tables", [])

    page_metas = [f for f in all_files if is_page_meta(f)]
    count = 0
    warnings = []

    for meta_path in page_metas:
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        slug = slug_from_meta_path(meta_path, content_src)

        for field in required:
            val = data.get(field, "")
            if not isinstance(val, str) or not val.strip():
                console.print(
                    f"[red]ERROR: Missing required \"{field}\" in {meta_path}[/red]"
                )
                continue

        note_type = data.get("type", "")
        if note_type not in valid_types:
            console.print(
                f"[red]ERROR: Invalid type \"{note_type}\" in {meta_path}[/red]"
            )
            continue

        scalar_vals = {k: data.get(k) for k in scalar}

        conn.execute(
            """
            INSERT OR REPLACE INTO notes
                (id, slug, title, description, type, domain, status,
                 review_cycle, last_reviewed, closure_score, closure_status,
                 icon, decision_status, date_decided, date_started, date_completed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"], slug, data["title"], data["description"], data["type"],
                scalar_vals.get("domain"),
                scalar_vals.get("status"),
                scalar_vals.get("review_cycle"),
                scalar_vals.get("last_reviewed"),
                scalar_vals.get("closure_score"),
                scalar_vals.get("closure_status"),
                scalar_vals.get("icon"),
                scalar_vals.get("decision_status"),
                scalar_vals.get("date_decided"),
                scalar_vals.get("date_started"),
                scalar_vals.get("date_completed"),
            ),
        )

        _ingest_note_arrays(conn, data, edge_tables)
        count += 1

    conn.commit()
    console.print(f"[green]  Ingested {count} notes[/green]")


def _ingest_note_arrays(
    conn: sqlite3.Connection, data: dict, edge_tables: list[dict]
) -> None:
    """Process all array fields on a note into their respective tables."""
    note_id = data["id"]

    for entry in edge_tables:
        field = entry["field"]
        table = entry["table"]
        values = data.get(field)
        if not values or not isinstance(values, list):
            continue

        if entry.get("normalized"):
            for val in values:
                conn.execute(
                    "INSERT OR IGNORE INTO tags (tag) VALUES (?)", (val,)
                )
                tag_id = conn.execute(
                    "SELECT tag_id FROM tags WHERE tag = ?", (val,)
                ).fetchone()[0]
                conn.execute(
                    "INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)",
                    (note_id, tag_id),
                )
        elif entry.get("style") == "owned":
            if table == "aliases":
                for val in values:
                    conn.execute(
                        "INSERT INTO aliases (alias, note_id) VALUES (?, ?)",
                        (val, note_id),
                    )
            elif table == "open_questions":
                for val in values:
                    conn.execute(
                        "INSERT INTO open_questions (question, note_id) VALUES (?, ?)",
                        (val, note_id),
                    )
        elif entry.get("style") == "edge":
            for val in values:
                conn.execute(
                    f"INSERT OR IGNORE INTO [{table}] (note_id, target_key) VALUES (?, ?)",
                    (note_id, val),
                )
        elif entry.get("style") == "literal":
            for val in values:
                conn.execute(
                    f"INSERT OR IGNORE INTO [{table}] (note_id, value) VALUES (?, ?)",
                    (note_id, val),
                )


# ── Key-to-note lookup ───────────────────────────────────────────────────

def build_key_to_note(conn: sqlite3.Connection) -> None:
    """Populate key_to_note from note id, slug, slug-derived wiki key, and aliases."""
    conn.execute("DELETE FROM key_to_note")

    rows = conn.execute("SELECT id, slug FROM notes").fetchall()
    for row in rows:
        note_id = row["id"]
        slug = row["slug"]

        conn.execute(
            "INSERT OR IGNORE INTO key_to_note (key, note_id) VALUES (?, ?)",
            (note_id, note_id),
        )

        if slug:
            conn.execute(
                "INSERT OR IGNORE INTO key_to_note (key, note_id) VALUES (?, ?)",
                (slug, note_id),
            )

        wiki_key = to_wiki_key(slug)
        if wiki_key:
            conn.execute(
                "INSERT OR IGNORE INTO key_to_note (key, note_id) VALUES (?, ?)",
                (wiki_key, note_id),
            )

        kebab_key = _camel_to_kebab(slug.rsplit("/", 1)[-1] if "/" in slug else slug)
        kebab_norm = kebab_key.replace("-", "_").lower()
        if kebab_norm and kebab_norm != wiki_key:
            conn.execute(
                "INSERT OR IGNORE INTO key_to_note (key, note_id) VALUES (?, ?)",
                (kebab_norm, note_id),
            )

    alias_rows = conn.execute("SELECT alias, note_id FROM aliases").fetchall()
    for row in alias_rows:
        normalized = row["alias"].replace("-", "_").replace(" ", "_").lower()
        conn.execute(
            "INSERT OR IGNORE INTO key_to_note (key, note_id) VALUES (?, ?)",
            (normalized, row["note_id"]),
        )

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM key_to_note").fetchone()[0]
    console.print(f"[green]  Built key_to_note lookup: {total} keys[/green]")


# ── Folder navigation ────────────────────────────────────────────────────

def ingest_folders(
    conn: sqlite3.Connection, content_src: str, schema: dict, all_files: list[str]
) -> None:
    """Read all meta.json folder navigation files."""
    folder_cfg = schema.get("folder_fields", {})
    folder_metas = [f for f in all_files if is_folder_meta(f)]
    count = 0

    for meta_path in folder_metas:
        raw_rel = os.path.relpath(os.path.dirname(meta_path), content_src)
        raw_posix = raw_rel.replace(os.sep, "/")

        dir_name = os.path.basename(os.path.dirname(meta_path))
        if dir_name.startswith("(") and dir_name.endswith(")"):
            continue

        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        folder_path = strip_folder_groups(raw_posix)
        if folder_path == "." or folder_path == "":
            folder_path = ""

        parent_path = None
        if "/" in folder_path:
            parent_path = folder_path.rsplit("/", 1)[0]
        elif folder_path:
            parent_path = ""

        title = data.get("title")
        icon = data.get("icon")
        default_open = 1 if data.get("defaultOpen") else 0

        conn.execute(
            """
            INSERT OR REPLACE INTO folders
                (folder_path, title, icon, default_open, parent_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (folder_path, title, icon, default_open, parent_path),
        )

        pages = data.get("pages", [])
        for i, page in enumerate(pages):
            if isinstance(page, str) and not page.startswith("---"):
                conn.execute(
                    "INSERT OR IGNORE INTO folder_pages (folder_path, page_slug, sort_order) VALUES (?, ?, ?)",
                    (folder_path, page, i),
                )

        count += 1

    conn.commit()
    console.print(f"[green]  Ingested {count} folder navigation files[/green]")


# ── MDX body processing ─────────────────────────────────────────────────

def process_mdx_bodies(
    conn: sqlite3.Connection, content_src: str, schema: dict, all_files: list[str]
) -> None:
    """Extract wiki links and sections from MDX body files."""
    wiki_cfg = schema.get("wiki_link_extraction", {})
    section_cfg = schema.get("body_section_extraction", {})
    mdx_files = [f for f in all_files if is_mdx_body(f)]

    wiki_count = 0
    section_count = 0

    for mdx_path in mdx_files:
        slug = slug_from_mdx_path(mdx_path, content_src)

        with open(mdx_path, "r", encoding="utf-8") as f:
            body = f.read()

        if wiki_cfg.get("enabled"):
            links = extract_wiki_links(body, wiki_cfg["pattern"])
            for link in links:
                conn.execute(
                    "INSERT INTO wiki_links (source_slug, target_raw, target_key) VALUES (?, ?, ?)",
                    (slug, link["target_raw"], link["target_key"]),
                )
            wiki_count += len(links)

        if section_cfg.get("enabled"):
            sections = split_sections(body, section_cfg["heading_pattern"])
            note_row = conn.execute(
                "SELECT id FROM notes WHERE slug = ?", (slug,)
            ).fetchone()
            if note_row:
                note_id = note_row["id"]
                for sec in sections:
                    conn.execute(
                        """
                        INSERT INTO note_sections
                            (note_id, heading, heading_level, sort_order, body)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            note_id,
                            sec["heading"],
                            sec["heading_level"],
                            sec["sort_order"],
                            sec["body"],
                        ),
                    )
                    section_count += 1

    conn.commit()
    if wiki_cfg.get("enabled"):
        console.print(f"[green]  Extracted {wiki_count} wiki links[/green]")
    if section_cfg.get("enabled"):
        console.print(f"[green]  Extracted {section_count} body sections[/green]")


# ── Library registry ─────────────────────────────────────────────────────

def ingest_library_registry(
    conn: sqlite3.Connection, schema: dict
) -> None:
    """Read library-registry.data.json and populate library tables."""
    lib_cfg = schema.get("library_registry", {})
    if not lib_cfg.get("enabled"):
        return

    json_path = schema["paths"]["library_registry_json"]
    if not os.path.exists(json_path):
        console.print(
            f"[yellow]  Library registry JSON not found: {json_path} — skipping[/yellow]"
        )
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    section_tbl = lib_cfg["section_table"]
    library_tbl = lib_cfg["library_table"]
    alt_tbl = lib_cfg["alternatives_table"]
    link_tbl = lib_cfg["note_link_table"]
    link_field = lib_cfg["note_link_field"]

    for sec in data.get("sections", []):
        conn.execute(
            f"""
            INSERT OR REPLACE INTO [{section_tbl}] (id, title, goal, sort_order)
            VALUES (?, ?, ?, ?)
            """,
            (sec["id"], sec["title"], sec["goal"], sec["sort_order"]),
        )

    lib_count = 0
    for lib in data.get("libraries", []):
        conn.execute(
            f"""
            INSERT OR REPLACE INTO [{library_tbl}]
                (number, name, section_id, function, tool_type, github_url,
                 pypi_name, latest_version, last_updated, github_description,
                 github_stars, github_license, pypi_summary, citation,
                 pro, con, docs_tag, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lib.get("number"),
                lib.get("name"),
                lib.get("section_id"),
                lib.get("function"),
                lib.get("tool_type"),
                lib.get("github_url"),
                lib.get("pypi_name"),
                lib.get("latest_version"),
                lib.get("last_updated"),
                lib.get("github_description"),
                lib.get("github_stars"),
                lib.get("github_license"),
                lib.get("pypi_summary"),
                lib.get("citation"),
                lib.get("pro"),
                lib.get("con"),
                lib.get("docs_tag"),
                lib.get("synced_at"),
            ),
        )

        for alt in lib.get("alternatives", []):
            conn.execute(
                f"INSERT OR IGNORE INTO [{alt_tbl}] (library_number, alternative) VALUES (?, ?)",
                (lib["number"], alt),
            )

        docs_tag = lib.get(link_field)
        if docs_tag:
            note_row = conn.execute(
                "SELECT id FROM notes WHERE slug = ?", (docs_tag,)
            ).fetchone()
            if note_row:
                conn.execute(
                    f"INSERT OR IGNORE INTO [{link_tbl}] (library_number, note_id) VALUES (?, ?)",
                    (lib["number"], note_row["id"]),
                )

        lib_count += 1

    conn.commit()
    sec_count = len(data.get("sections", []))
    console.print(
        f"[green]  Ingested {sec_count} lib sections, {lib_count} libraries[/green]"
    )


# ── JSON-LD export ───────────────────────────────────────────────────────

def export_jsonld(conn: sqlite3.Connection, schema: dict) -> None:
    """Export the KG as a JSON-LD file."""
    jsonld_cfg = schema.get("jsonld", {})
    if not jsonld_cfg.get("enabled"):
        return

    output_path = schema["paths"]["jsonld_output"]
    base_uri = jsonld_cfg["base_uri"]
    namespaces = jsonld_cfg.get("namespaces", {})

    context = {"@base": base_uri}
    context.update(namespaces)

    graph = []

    rows = conn.execute("SELECT * FROM notes").fetchall()
    for row in rows:
        node = {
            "@id": f"note:{row['id']}",
            "@type": f"sr:{row['type']}",
            "dcterms:title": row["title"],
            "dcterms:description": row["description"],
            "sr:slug": row["slug"],
        }
        if row["domain"]:
            node["sr:domain"] = row["domain"]
        if row["status"]:
            node["sr:status"] = row["status"]
        if row["closure_score"] is not None:
            node["sr:closureScore"] = row["closure_score"]
        graph.append(node)

    lib_cfg = schema.get("library_registry", {})
    if lib_cfg.get("enabled"):
        lib_tbl = lib_cfg["library_table"]
        lib_rows = conn.execute(f"SELECT * FROM [{lib_tbl}]").fetchall()
        for row in lib_rows:
            node = {
                "@id": f"lib:{row['number']}",
                "@type": "sr:Library",
                "schema:name": row["name"],
                "sr:function": row["function"] or "",
                "sr:toolType": row["tool_type"] or "",
            }
            if row["github_url"]:
                node["schema:codeRepository"] = row["github_url"]
            graph.append(node)

    doc = {"@context": context, "@graph": graph}

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)

    size_kb = os.path.getsize(output_path) / 1024
    console.print(
        f"[green]  JSON-LD written: {output_path} ({size_kb:.1f} KB, {len(graph)} nodes)[/green]"
    )


# ── Closure validation ───────────────────────────────────────────────────

def _safe_count(conn: sqlite3.Connection, table: str, note_id: str) -> int:
    """Count rows in a table for a note, returning 0 if the table doesn't exist."""
    try:
        return conn.execute(
            f"SELECT COUNT(*) FROM [{table}] WHERE note_id = ?", (note_id,)
        ).fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def run_closure_warnings(conn: sqlite3.Connection, schema: dict) -> None:
    """Evaluate closure rules from config against every note."""
    closure_cfg = schema.get("closure_rules", {})
    if not closure_cfg.get("enabled"):
        return

    rules = closure_cfg.get("rules", [])
    rows = conn.execute("SELECT * FROM notes").fetchall()
    warn_count = 0

    for row in rows:
        issues = []
        note_type = row["type"]

        for rule in rules:
            if note_type not in rule["applies_to"]:
                continue

            check = rule["check"]
            if check == "edge_count":
                total = sum(_safe_count(conn, t, row["id"]) for t in rule["tables"])
                if total < rule["min"]:
                    issues.append(rule["label"])
            elif check == "scalar_set":
                for field in rule["fields"]:
                    if not row[field]:
                        issues.append(rule["label"])
                        break

        if issues:
            console.print(
                f"[yellow]  CLOSURE [{note_type}] {row['title']} ({row['id']}): "
                f"{', '.join(issues)}[/yellow]"
            )
            warn_count += 1

    if warn_count:
        console.print(f"[yellow]  {warn_count} note(s) with closure gaps[/yellow]")
    else:
        console.print("[green]  All notes pass closure checks[/green]")


# ── Orchestrator ─────────────────────────────────────────────────────────

def run(config_path: str) -> None:
    """Full pipeline: load config → create DB → ingest → export."""
    console.rule("[bold blue]KG Builder[/bold blue]")

    with open(config_path, "r", encoding="utf-8") as f:
        schema = yaml.safe_load(f)

    content_src = schema["paths"]["content_src"]
    db_path = schema["paths"]["db_output"]

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = get_connection(db_path, schema)

    console.print("[bold]1. Scanning content-src...[/bold]")
    all_files = list_files_recursive(content_src)
    console.print(f"   Found {len(all_files)} files")

    console.print("[bold]2. Ingesting notes...[/bold]")
    ingest_notes(conn, content_src, schema, all_files)

    console.print("[bold]3. Building key_to_note lookup...[/bold]")
    build_key_to_note(conn)

    console.print("[bold]4. Ingesting folder navigation...[/bold]")
    ingest_folders(conn, content_src, schema, all_files)

    console.print("[bold]5. Processing MDX bodies...[/bold]")
    process_mdx_bodies(conn, content_src, schema, all_files)

    console.print("[bold]6. Ingesting library registry...[/bold]")
    ingest_library_registry(conn, schema)

    console.print("[bold]7. Running closure checks...[/bold]")
    run_closure_warnings(conn, schema)

    jsonld_cfg = schema.get("jsonld", {})
    if jsonld_cfg.get("enabled"):
        console.print("[bold]8. Exporting JSON-LD...[/bold]")
        export_jsonld(conn, schema)

    total_notes = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    total_edges = 0
    for entry in schema.get("array_edge_tables", []):
        tbl = entry["table"]
        if entry.get("normalized") or entry.get("style") == "owned":
            continue
        try:
            total_edges += conn.execute(f"SELECT COUNT(*) FROM [{tbl}]").fetchone()[0]
        except sqlite3.OperationalError:
            pass

    conn.close()

    size_kb = os.path.getsize(db_path) / 1024
    console.print(f"\n[bold green]Done.[/bold green]")
    console.print(f"   Database: {db_path} ({size_kb:.1f} KB)")
    console.print(f"   Notes: {total_notes}")
    console.print(f"   Edges: {total_edges}")
    console.rule("[bold blue]Complete[/bold blue]")


# ── CLI entry point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build a SQLite knowledge graph from content-src metadata"
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to YAML schema config",
    )
    args = parser.parse_args()
    run(config_path=args.config)
