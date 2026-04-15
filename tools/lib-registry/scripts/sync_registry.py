"""
PURPOSE: Sync library metadata from config/*.yaml into registry.sqlite3.

OWNS:
  - Reading config/sections.yaml, config/libraries.yaml, config/settings.yaml
  - Rolling backups of registry.sqlite3 and libraries.yaml (5-deep)
  - Staleness detection with automatic full-refresh
  - Incremental change detection (probe before full fetch)
  - Validating library names against GitHub repos and PyPI
  - Fetching latest version and last-updated timestamps
  - Upserting changed data into the SQLite database
  - Writing data/sync.log (overwritten each run) with failed endpoints

TOUCH POINTS:
  - Reads config/*.yaml (all tunables from settings.yaml)
  - Writes to data/registry.sqlite3 via db_schema.py
  - Writes to data/sync.log (overwritten, not appended)
  - Writes rolling backups to backups/
  - Optionally uses GITHUB_TOKEN env var for higher API rate limits
"""

import glob
import json
import logging
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone

import requests
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from db_schema import DB_PATH, get_connection

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
SECTIONS_PATH = os.path.join(CONFIG_DIR, "sections.yaml")
LIBRARIES_PATH = os.path.join(CONFIG_DIR, "libraries.yaml")
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.yaml")

DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_PATH = os.path.join(DATA_DIR, "sync.log")
JSON_OUT_PATH = os.path.join(DATA_DIR, "library-registry.data.json")
SITE_OUT_PATH = os.path.join(BASE_DIR, "site-out", "library-registry", "library-registry.data.json")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

_failures: list[dict] = []

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("sync_registry")


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def _load_settings() -> dict:
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


SETTINGS = _load_settings()

GITHUB_API = SETTINGS["api"]["github_base_url"]
PYPI_API = SETTINGS["api"]["pypi_base_url"]
REQUEST_TIMEOUT = SETTINGS["requests"]["timeout_seconds"]
GITHUB_SLEEP = SETTINGS["requests"]["github_sleep_seconds"]


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

def _rotate_backups() -> list[str]:
    """Snapshot DB + libraries.yaml into backups/, keeping at most max_copies.

    Returns a list of backup filenames created this run.
    """
    backup_dir = os.path.join(BASE_DIR, SETTINGS["backup"]["directory"])
    max_copies = SETTINGS["backup"]["max_copies"]
    os.makedirs(backup_dir, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    sources = [
        (DB_PATH, "registry.sqlite3"),
        (LIBRARIES_PATH, "libraries.yaml"),
    ]

    created: list[str] = []
    for src_path, base_name in sources:
        if not os.path.exists(src_path):
            continue

        dest_name = f"{base_name}.{today}.bak"
        dest = os.path.join(backup_dir, dest_name)
        shutil.copy2(src_path, dest)
        created.append(dest_name)
        log.info("Backup: %s -> %s", base_name, dest)

        existing = sorted(glob.glob(
            os.path.join(backup_dir, f"{base_name}.*.bak")
        ))
        while len(existing) > max_copies:
            oldest = existing.pop(0)
            os.remove(oldest)
            log.info("Backup pruned: %s", oldest)

    return created


# ---------------------------------------------------------------------------
# Staleness
# ---------------------------------------------------------------------------

def _check_staleness(conn: sqlite3.Connection) -> int | None:
    """Return days since newest sync, or None if the DB is empty."""
    row = conn.execute(
        "SELECT MAX(synced_at) as newest FROM libraries"
    ).fetchone()
    if not row or not row["newest"]:
        return None
    newest = datetime.fromisoformat(row["newest"])
    age = datetime.now(timezone.utc) - newest
    return age.days


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def github_headers() -> dict:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def parse_github_owner_repo(url: str) -> tuple[str, str] | None:
    """Extract owner/repo from a GitHub URL. Returns None for non-GitHub URLs."""
    if "github.com/" not in url:
        return None
    parts = url.rstrip("/").split("github.com/")[-1].split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None


def fetch_github_info(owner: str, repo: str) -> dict:
    """Fetch repo metadata from GitHub API."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    try:
        resp = requests.get(url, headers=github_headers(), timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            license_info = data.get("license") or {}
            return {
                "name": data.get("name", ""),
                "full_name": data.get("full_name", ""),
                "description": data.get("description", ""),
                "pushed_at": data.get("pushed_at", ""),
                "stars": data.get("stargazers_count", 0),
                "license": license_info.get("spdx_id", ""),
            }
        _failures.append({"endpoint": url, "status": resp.status_code, "error": ""})
        log.warning("GitHub API %s/%s returned %d", owner, repo, resp.status_code)
    except requests.RequestException as e:
        _failures.append({"endpoint": url, "status": 0, "error": str(e)})
        log.warning("GitHub API error for %s/%s: %s", owner, repo, e)
    return {}


def fetch_github_latest_tag(owner: str, repo: str) -> dict:
    """Fetch the latest tag/release version and its date from GitHub.

    Returns {"version": str, "date": str} or empty dict.
    Tries releases first (has published_at), then falls back to tags
    and fetches the commit date for that tag.
    """
    release_url = f"{GITHUB_API}/repos/{owner}/{repo}/releases/latest"
    try:
        resp = requests.get(release_url, headers=github_headers(), timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "version": data.get("tag_name", ""),
                "date": data.get("published_at", ""),
            }
    except requests.RequestException:
        pass

    tags_url = f"{GITHUB_API}/repos/{owner}/{repo}/tags"
    try:
        resp = requests.get(tags_url, headers=github_headers(), timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            tags = resp.json()
            if tags:
                tag_name = tags[0].get("name", "")
                commit_sha = tags[0].get("commit", {}).get("sha", "")
                tag_date = ""
                if commit_sha:
                    tag_date = _fetch_commit_date(owner, repo, commit_sha)
                return {"version": tag_name, "date": tag_date}
    except requests.RequestException:
        pass

    _failures.append({"endpoint": release_url, "status": 0, "error": "no release or tag found"})
    return {}


def _fetch_commit_date(owner: str, repo: str, sha: str) -> str:
    """Fetch the commit date for a given SHA."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits/{sha}"
    try:
        resp = requests.get(url, headers=github_headers(), timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            commit_info = resp.json().get("commit", {})
            return commit_info.get("committer", {}).get("date", "")
    except requests.RequestException:
        pass
    return ""


def fetch_pypi_info(package_name: str) -> dict:
    """Fetch latest version, upload time, and summary from PyPI."""
    url = f"{PYPI_API}/{package_name}/json"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            info = data.get("info", {})
            version = info.get("version", "")
            summary = info.get("summary", "")
            releases = data.get("releases", {})
            upload_time = ""
            if version and version in releases and releases[version]:
                upload_time = releases[version][-1].get("upload_time_iso_8601", "")
            return {"version": version, "upload_time": upload_time, "summary": summary}
        _failures.append({"endpoint": url, "status": resp.status_code, "error": ""})
        log.warning("PyPI %s returned %d", package_name, resp.status_code)
    except requests.RequestException as e:
        _failures.append({"endpoint": url, "status": 0, "error": str(e)})
        log.warning("PyPI error for %s: %s", package_name, e)
    return {}


def validate_name_against_repo(
    lib_name: str,
    repo_name: str,
    repo_full_name: str,
    github_desc: str,
    pypi_name: str | None,
    github_url: str = "",
    repo_aliases: list[str] | None = None,
) -> bool:
    """Check that the library name plausibly matches the repo.

    Checks (in order, any match = pass):
      1. repo_aliases from config (explicit override, always trusted)
      2. lib_name words appear in the repo name, full_name, URL, or description
      3. pypi_name appears in the repo name or description
      4. repo name appears in the lib_name (catches e.g. "flair" in "HunFlair2")
      5. description words appear in the lib_name
    """
    def normalise(s: str) -> str:
        return s.lower().replace("-", " ").replace("_", " ").replace(".", " ")

    if repo_aliases:
        return True

    lib_norm = normalise(lib_name)
    lib_words = [w for w in lib_norm.split() if len(w) > 2]
    targets = [
        normalise(repo_name),
        normalise(repo_full_name),
        normalise(github_desc or ""),
        normalise(github_url),
    ]
    if pypi_name:
        lib_words.append(normalise(pypi_name))

    for word in lib_words:
        for target in targets:
            if word in target:
                return True

    repo_norm = normalise(repo_name)
    repo_words = [w for w in repo_norm.split() if len(w) > 2]
    for rw in repo_words:
        if rw in lib_norm:
            return True

    desc_norm = normalise(github_desc or "")
    desc_words = [w for w in desc_norm.split() if len(w) > 2]
    for dw in desc_words:
        if dw in lib_norm:
            return True

    return False


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------

def _has_changed(
    lib: dict,
    db_row: sqlite3.Row | None,
    pypi_result: dict | None,
    gh_info: dict | None,
) -> bool:
    """Return True if upstream data differs from stored DB values."""
    if db_row is None:
        return True

    if pypi_result:
        upstream_ver = pypi_result.get("version", "")
        if upstream_ver and upstream_ver != (db_row["latest_version"] or ""):
            return True

    if gh_info:
        if gh_info.get("pushed_at", "") != (db_row["github_pushed_at"] or ""):
            return True
        if gh_info.get("stars", 0) != (db_row["github_stars"] or 0):
            return True
        if gh_info.get("description", "") != (db_row["github_description"] or ""):
            return True
        if gh_info.get("license", "") != (db_row["github_license"] or ""):
            return True

    return False


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------

def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Main sync
# ---------------------------------------------------------------------------

def sync():
    force = "--force" in sys.argv

    log.info("Loading config from %s", CONFIG_DIR)

    sections_data = load_yaml(SECTIONS_PATH)
    libraries_data = load_yaml(LIBRARIES_PATH)

    if not sections_data or "sections" not in sections_data:
        log.error("Invalid sections.yaml")
        sys.exit(1)
    if not libraries_data:
        log.error("Invalid libraries.yaml")
        sys.exit(1)

    # ---- Backup (every run, before any writes) ----
    backup_files = _rotate_backups()

    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()

    # ---- Staleness check ----
    staleness_days: int | None = None
    mode = "force" if force else "incremental"
    if not force and SETTINGS["staleness"]["auto_force"]:
        staleness_days = _check_staleness(conn)
        if staleness_days is None:
            log.warning("Empty database — forcing full refresh.")
            force = True
            mode = "force (empty database)"
        elif staleness_days >= SETTINGS["staleness"]["max_age_days"]:
            log.warning(
                "Staleness detected: newest sync is %d days old (threshold: %d). "
                "Forcing full refresh.",
                staleness_days,
                SETTINGS["staleness"]["max_age_days"],
            )
            force = True
            mode = f"force (staleness: {staleness_days} days)"

    if force and mode == "force":
        mode = "force (manual)"

    log.info("Sync mode: %s", mode)

    # ---- Sections ----
    section_ids = set()
    for sec in sections_data["sections"]:
        section_ids.add(sec["id"])
        conn.execute(
            """
            INSERT INTO sections (id, title, goal, sort_order)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                goal = excluded.goal,
                sort_order = excluded.sort_order
            """,
            (sec["id"], sec["title"], sec["goal"], sec["sort_order"]),
        )
    conn.commit()
    log.info("Synced %d sections", len(section_ids))

    # ---- Libraries ----
    updated = 0
    unchanged = 0
    errors = 0

    for lib in libraries_data:
        name = lib["name"]
        number = lib["number"]

        if lib["section"] not in section_ids:
            log.error("#%d %s: unknown section '%s'", number, name, lib["section"])
            errors += 1
            continue

        # Fetch current DB row for comparison
        db_row = conn.execute(
            "SELECT * FROM libraries WHERE number = ?", (number,)
        ).fetchone()

        # ---- Probe phase: lightweight API calls ----
        pypi_result: dict | None = None
        if lib.get("pypi_name"):
            pypi_result = fetch_pypi_info(lib["pypi_name"])

        gh_info: dict | None = None
        gh_parsed = parse_github_owner_repo(lib.get("github_url", ""))
        if gh_parsed:
            owner, repo = gh_parsed
            gh_info = fetch_github_info(owner, repo)

        # ---- Change detection (skip if not --force) ----
        if not force and not _has_changed(lib, db_row, pypi_result, gh_info):
            log.info("#%d %s: unchanged, skipping", number, name)
            unchanged += 1
            if gh_parsed:
                time.sleep(GITHUB_SLEEP)
            continue

        # ---- Full fetch phase (only for changed libraries) ----
        latest_version = ""
        last_updated = ""
        github_description = ""
        github_stars = 0
        github_license = ""
        github_pushed_at = ""
        pypi_summary = ""

        if pypi_result:
            latest_version = pypi_result.get("version", "")
            last_updated = pypi_result.get("upload_time", "")
            pypi_summary = pypi_result.get("summary", "")
            log.info(
                "#%d %s: PyPI v%s (%s)",
                number,
                name,
                latest_version,
                last_updated[:10] if last_updated else "?",
            )

        if gh_parsed and gh_info:
            owner, repo = gh_parsed
            github_description = gh_info.get("description", "")
            github_stars = gh_info.get("stars", 0)
            github_license = gh_info.get("license", "")
            github_pushed_at = gh_info.get("pushed_at", "")

            is_valid = validate_name_against_repo(
                lib_name=name,
                repo_name=gh_info.get("name", repo),
                repo_full_name=gh_info.get("full_name", f"{owner}/{repo}"),
                github_desc=gh_info.get("description", ""),
                pypi_name=lib.get("pypi_name"),
                github_url=lib.get("github_url", ""),
                repo_aliases=lib.get("repo_aliases"),
            )
            if not is_valid:
                _failures.append({
                    "endpoint": lib.get("github_url", ""),
                    "status": "name_mismatch",
                    "error": f"'{name}' not found in repo '{gh_info.get('full_name', '')}': '{(gh_info.get('description') or '')[:80]}'",
                })
                log.warning(
                    "#%d %s: name may not match repo '%s'",
                    number,
                    name,
                    gh_info.get("full_name", f"{owner}/{repo}"),
                )

            if not latest_version:
                tag_info = fetch_github_latest_tag(owner, repo)
                if tag_info.get("version"):
                    latest_version = tag_info["version"]
                    if tag_info.get("date"):
                        last_updated = tag_info["date"]
                    log.info(
                        "#%d %s: GitHub tag %s (%s)",
                        number, name, latest_version,
                        last_updated[:10] if last_updated else "no date",
                    )

            if not last_updated and gh_info.get("pushed_at"):
                last_updated = gh_info["pushed_at"]

            time.sleep(GITHUB_SLEEP)

        alternatives_json = json.dumps(lib.get("alternatives", []))

        conn.execute(
            """
            INSERT INTO libraries (
                number, name, section_id, function, tool_type,
                github_url, pypi_name, latest_version, last_updated,
                github_description, github_stars, github_license,
                github_pushed_at, pypi_summary,
                citation, pro, con, alternatives, docs_tag, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(number) DO UPDATE SET
                name = excluded.name,
                section_id = excluded.section_id,
                function = excluded.function,
                tool_type = excluded.tool_type,
                github_url = excluded.github_url,
                pypi_name = excluded.pypi_name,
                latest_version = excluded.latest_version,
                last_updated = excluded.last_updated,
                github_description = excluded.github_description,
                github_stars = excluded.github_stars,
                github_license = excluded.github_license,
                github_pushed_at = excluded.github_pushed_at,
                pypi_summary = excluded.pypi_summary,
                citation = excluded.citation,
                pro = excluded.pro,
                con = excluded.con,
                alternatives = excluded.alternatives,
                docs_tag = excluded.docs_tag,
                synced_at = excluded.synced_at
            """,
            (
                number,
                name,
                lib["section"],
                lib.get("function", ""),
                lib.get("tool_type", ""),
                lib.get("github_url", ""),
                lib.get("pypi_name"),
                latest_version,
                last_updated,
                github_description,
                github_stars,
                github_license,
                github_pushed_at,
                pypi_summary,
                lib.get("citation", ""),
                lib.get("pro", ""),
                lib.get("con", ""),
                alternatives_json,
                lib.get("docs_tag"),
                now,
            ),
        )
        updated += 1

    conn.commit()
    conn.close()

    write_sync_log(now, mode, updated, unchanged, errors, backup_files)
    export_json()
    log.info(
        "Done: mode=%s, updated=%d, unchanged=%d, errors=%d",
        mode, updated, unchanged, errors,
    )


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def export_json() -> None:
    """Read the DB and write a JSON file for the Fumadocs site component."""
    conn = get_connection()

    sections = []
    for row in conn.execute("SELECT id, title, goal, sort_order FROM sections ORDER BY sort_order"):
        sections.append({
            "id": row["id"],
            "title": row["title"],
            "goal": row["goal"],
            "sort_order": row["sort_order"],
        })

    libraries = []
    for row in conn.execute(
        """SELECT l.*, s.title as section_title, s.sort_order
           FROM libraries l
           JOIN sections s ON l.section_id = s.id
           ORDER BY s.sort_order, l.number"""
    ):
        libraries.append({
            "number": row["number"],
            "name": row["name"],
            "section_id": row["section_id"],
            "section_title": row["section_title"],
            "function": row["function"] or "",
            "tool_type": row["tool_type"] or "",
            "github_url": row["github_url"] or "",
            "pypi_name": row["pypi_name"],
            "latest_version": row["latest_version"] or "",
            "last_updated": row["last_updated"] or "",
            "github_description": row["github_description"] or "",
            "github_stars": row["github_stars"] or 0,
            "github_license": row["github_license"] or "",
            "github_pushed_at": row["github_pushed_at"] or "",
            "pypi_summary": row["pypi_summary"] or "",
            "citation": row["citation"] or "",
            "pro": row["pro"] or "",
            "con": row["con"] or "",
            "alternatives": json.loads(row["alternatives"] or "[]"),
            "docs_tag": row["docs_tag"],
            "synced_at": row["synced_at"] or "",
        })

    conn.close()

    output = {"sections": sections, "libraries": libraries}
    payload = json.dumps(output, indent=2, ensure_ascii=False)

    for out_path in (JSON_OUT_PATH, SITE_OUT_PATH):
        target_dir = os.path.dirname(out_path)
        if os.path.isdir(target_dir):
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(payload)
            log.info("JSON written to %s", out_path)
        else:
            log.warning("Skipping %s (directory not mounted)", out_path)


# ---------------------------------------------------------------------------
# Sync log
# ---------------------------------------------------------------------------

def write_sync_log(
    run_time: str,
    mode: str,
    updated: int,
    unchanged: int,
    errors: int,
    backup_files: list[str],
) -> None:
    """Overwrite data/sync.log with the results of this run."""
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write(f"sync_registry.py  —  {run_time}\n")
        f.write(
            f"mode: {mode}  |  updated: {updated}  |  unchanged: {unchanged}"
            f"  |  config_errors: {errors}  |  endpoint_failures: {len(_failures)}\n"
        )
        if backup_files:
            f.write(f"backups: {', '.join(backup_files)}\n")
        f.write("=" * 72 + "\n\n")

        if not _failures:
            f.write("All endpoints responded successfully.\n")
        else:
            for i, fail in enumerate(_failures, 1):
                f.write(f"[{i}] {fail['endpoint']}\n")
                f.write(f"    status: {fail['status']}\n")
                if fail.get("error"):
                    f.write(f"    error:  {fail['error']}\n")
                f.write("\n")

    log.info("Sync log written to %s (%d failures)", LOG_PATH, len(_failures))


if __name__ == "__main__":
    sync()
