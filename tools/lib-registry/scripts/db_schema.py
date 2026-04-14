"""
PURPOSE: SQLite schema creation for the library registry.

OWNS:
  - create_tables() — idempotent table creation
  - DB_PATH constant (read from config, not hardcoded)

TOUCH POINTS:
  - Called by sync_registry.py before any writes
  - Read by scripts/generate-lib-registry.ts on the site side
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "registry.sqlite3")


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sections (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            goal        TEXT NOT NULL,
            sort_order  INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS libraries (
            number              INTEGER PRIMARY KEY,
            name                TEXT NOT NULL,
            section_id          TEXT NOT NULL REFERENCES sections(id),
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
            alternatives        TEXT,
            docs_tag            TEXT,
            synced_at           TEXT
        );
        """
    )
    _migrate_add_columns(conn)
    conn.commit()


def _migrate_add_columns(conn: sqlite3.Connection) -> None:
    """Add columns that may be missing from an older schema."""
    existing = {
        row[1] for row in conn.execute("PRAGMA table_info(libraries)").fetchall()
    }
    migrations = [
        ("github_description", "TEXT"),
        ("github_stars", "INTEGER"),
        ("github_license", "TEXT"),
        ("pypi_summary", "TEXT"),
    ]
    for col, col_type in migrations:
        if col not in existing:
            conn.execute(f"ALTER TABLE libraries ADD COLUMN {col} {col_type}")



def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    create_tables(conn)
    return conn
