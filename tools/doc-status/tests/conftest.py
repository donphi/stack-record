"""
PURPOSE: Shared pytest fixtures and helpers for the doc-status test suite.

DESIGN:
  - There is no static fixture tree. Every test gets a fresh tmp_path
    content root that contains nothing but symlinks to the REAL
    _template/ directories under content-src/docs/. Tests then add notes
    programmatically via tests/factory.py.
  - Adding a new note type / new folder / new template to the real tree
    requires zero changes to test code.

OWNS:
  - Resolving the real content-src/docs/ path from config/tests.yaml
    (works in docker via the read-only mount and locally via a relative
    fallback)
  - Symlinking every real _template directory into a per-test tmp tree
  - Per-test app reload so each FastAPI app sees its own content tree
"""

from __future__ import annotations

import hashlib
import importlib
import os
import sys
from pathlib import Path
from typing import Any, Iterator

import pytest


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _set_config_env() -> None:
    os.environ["DOC_STATUS_CONFIG"] = str(PROJECT_ROOT / "config")


def _resolve_real_content_src(candidates: list[str]) -> Path | None:
    for raw in candidates:
        p = Path(raw)
        if not p.is_absolute():
            p = (PROJECT_ROOT / raw).resolve()
        if p.is_dir():
            return p
    return None


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def tests_cfg() -> dict[str, Any]:
    _set_config_env()
    from config_loader import load_tests_config
    return load_tests_config()


@pytest.fixture(scope="session")
def real_content_src(tests_cfg) -> Path:
    p = _resolve_real_content_src(tests_cfg["real_content_candidates"])
    if p is None:
        pytest.skip(
            f"real content tree not found in any of: {tests_cfg['real_content_candidates']}. "
            "Set DOC_STATUS_REAL_CONTENT or run via docker compose run --rm test."
        )
    return p


@pytest.fixture(scope="session")
def rules_cfg() -> dict[str, Any]:
    _set_config_env()
    from config_loader import load_rules_config
    return load_rules_config()


@pytest.fixture(scope="session")
def dashboard_cfg() -> dict[str, Any]:
    _set_config_env()
    from config_loader import load_dashboard_config
    return load_dashboard_config()


def _symlink_templates(real_content_src: Path, dst_root: Path) -> int:
    """Symlink every real _template directory into dst_root, mirroring
    the real folder structure. Returns the number of templates linked."""
    count = 0
    for tdir in sorted(real_content_src.rglob("_template")):
        if not tdir.is_dir():
            continue
        rel = tdir.relative_to(real_content_src)
        link = dst_root / rel
        link.parent.mkdir(parents=True, exist_ok=True)
        if not link.exists():
            os.symlink(tdir.resolve(), link, target_is_directory=True)
            count += 1
    return count


@pytest.fixture
def isolated_content(tmp_path: Path, real_content_src: Path) -> Path:
    """Per-test content root: empty except for symlinks to every real
    _template/ dir. Tests add notes via tests.factory."""
    n = _symlink_templates(real_content_src, tmp_path)
    assert n > 0, f"expected at least one _template under {real_content_src}"
    return tmp_path


@pytest.fixture
def configured_env(isolated_content: Path) -> Iterator[None]:
    _set_config_env()
    prev = os.environ.get("DOC_STATUS_CONTENT")
    os.environ["DOC_STATUS_CONTENT"] = str(isolated_content)
    yield
    if prev is None:
        os.environ.pop("DOC_STATUS_CONTENT", None)
    else:
        os.environ["DOC_STATUS_CONTENT"] = prev


@pytest.fixture
def fresh_server(configured_env: None):
    """Reload the server module so its module-level state.refresh() runs
    against the current isolated_content. Use this when you have NOT
    pre-populated the tree (e.g. just symlinked templates)."""
    import server as srv
    importlib.reload(srv)
    return srv


@pytest.fixture
def server_factory(configured_env: None):
    """Returns a no-arg callable that reloads the server module on demand.
    Use this when you want to populate the content tree FIRST, then start
    the server so its initial scan picks up the freshly generated notes."""
    def _make():
        import server as srv
        importlib.reload(srv)
        return srv
    return _make


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_tree(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not root.exists():
        return out
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            continue
        if path.is_file():
            rel = path.relative_to(root)
            out[str(rel)] = sha256_file(path)
    return out
