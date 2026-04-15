"""
PURPOSE: SQLite schema creation for the knowledge graph.

OWNS:
  - create_tables() — idempotent table creation driven by config
  - get_connection() — open/create DB at the config-specified path

TOUCH POINTS:
  - Called by build_kg.py before any writes
  - Schema is fully driven by config/schema.yaml — no hardcoded table names

HYPERPARAMETERS:
  - All externalized to config/schema.yaml
"""

import os
import sqlite3


def create_core_tables(conn: sqlite3.Connection) -> None:
    """Create the fixed node tables that always exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id              TEXT PRIMARY KEY,
            slug            TEXT NOT NULL UNIQUE,
            title           TEXT NOT NULL,
            description     TEXT NOT NULL,
            type            TEXT NOT NULL,
            domain          TEXT,
            status          TEXT,
            review_cycle    TEXT,
            last_reviewed   TEXT,
            closure_score   INTEGER,
            closure_status  TEXT,
            icon            TEXT,
            decision_status TEXT,
            date_decided    TEXT,
            date_started    TEXT,
            date_completed  TEXT
        );

        CREATE TABLE IF NOT EXISTS tags (
            tag_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            tag     TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS aliases (
            alias_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            alias       TEXT NOT NULL,
            note_id     TEXT NOT NULL REFERENCES notes(id)
        );

        CREATE TABLE IF NOT EXISTS open_questions (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            question    TEXT NOT NULL,
            note_id     TEXT NOT NULL REFERENCES notes(id)
        );

        CREATE TABLE IF NOT EXISTS folders (
            folder_path     TEXT PRIMARY KEY,
            title           TEXT,
            icon            TEXT,
            default_open    INTEGER,
            parent_path     TEXT REFERENCES folders(folder_path)
        );

        CREATE TABLE IF NOT EXISTS folder_pages (
            folder_path TEXT NOT NULL REFERENCES folders(folder_path),
            page_slug   TEXT NOT NULL,
            sort_order  INTEGER NOT NULL,
            PRIMARY KEY (folder_path, page_slug)
        );

        CREATE TABLE IF NOT EXISTS key_to_note (
            key     TEXT PRIMARY KEY,
            note_id TEXT NOT NULL REFERENCES notes(id)
        );

        CREATE TABLE IF NOT EXISTS wiki_links (
            source_slug TEXT NOT NULL,
            target_raw  TEXT NOT NULL,
            target_key  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS note_sections (
            section_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id         TEXT NOT NULL REFERENCES notes(id),
            heading         TEXT NOT NULL,
            heading_level   INTEGER NOT NULL,
            sort_order      INTEGER NOT NULL,
            body            TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS note_tags (
            note_id TEXT NOT NULL REFERENCES notes(id),
            tag_id  INTEGER NOT NULL REFERENCES tags(tag_id),
            PRIMARY KEY (note_id, tag_id)
        );
        """
    )
    conn.commit()


def create_edge_table(conn: sqlite3.Connection, table: str, style: str) -> None:
    """Create a single edge/owned/literal junction table if it doesn't exist."""
    if style == "edge":
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS [{table}] (
                note_id     TEXT NOT NULL REFERENCES notes(id),
                target_key  TEXT NOT NULL,
                PRIMARY KEY (note_id, target_key)
            )
            """
        )
    elif style == "literal":
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS [{table}] (
                note_id TEXT NOT NULL REFERENCES notes(id),
                value   TEXT NOT NULL,
                PRIMARY KEY (note_id, value)
            )
            """
        )
    conn.commit()


def create_library_tables(conn: sqlite3.Connection, cfg: dict) -> None:
    """Create library registry tables from config."""
    section_tbl = cfg["section_table"]
    library_tbl = cfg["library_table"]
    alt_tbl = cfg["alternatives_table"]
    link_tbl = cfg["note_link_table"]

    conn.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS [{section_tbl}] (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            goal        TEXT NOT NULL,
            sort_order  INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS [{library_tbl}] (
            number              INTEGER PRIMARY KEY,
            name                TEXT NOT NULL,
            section_id          TEXT NOT NULL REFERENCES [{section_tbl}](id),
            function            TEXT,
            tool_type           TEXT,
            github_url          TEXT,
            pypi_name           TEXT,
            latest_version      TEXT,
            last_updated        TEXT,
            github_description  TEXT,
            github_stars        INTEGER,
            github_license      TEXT,
            pypi_summary        TEXT,
            citation            TEXT,
            pro                 TEXT,
            con                 TEXT,
            docs_tag            TEXT,
            synced_at           TEXT
        );

        CREATE TABLE IF NOT EXISTS [{alt_tbl}] (
            library_number  INTEGER NOT NULL REFERENCES [{library_tbl}](number),
            alternative     TEXT NOT NULL,
            PRIMARY KEY (library_number, alternative)
        );

        CREATE TABLE IF NOT EXISTS [{link_tbl}] (
            library_number  INTEGER NOT NULL REFERENCES [{library_tbl}](number),
            note_id         TEXT NOT NULL REFERENCES notes(id),
            PRIMARY KEY (library_number, note_id)
        );
        """
    )
    conn.commit()


def create_tables(conn: sqlite3.Connection, schema: dict) -> None:
    """Idempotent full schema creation driven by the loaded YAML config."""
    create_core_tables(conn)

    for entry in schema.get("array_edge_tables", []):
        if entry.get("normalized"):
            continue
        style = entry.get("style", "edge")
        if entry["table"] in ("aliases", "open_questions"):
            continue
        create_edge_table(conn, entry["table"], style)

    lib_cfg = schema.get("library_registry", {})
    if lib_cfg.get("enabled"):
        create_library_tables(conn, lib_cfg)


def get_connection(db_path: str, schema: dict) -> sqlite3.Connection:
    """Open or create the database and ensure all tables exist."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn, schema)
    return conn
