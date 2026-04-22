"""Round-trip integration tests — the user's stated concern.

Each test:
  1. Generates a note from the real templates
  2. Records the on-disk bytes for every file in the tree
  3. Issues a PATCH via the FastAPI app
  4. Re-reads the targeted file from disk
  5. Asserts the change persisted, AND no other file changed
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from tests.factory import make_note


pytestmark = pytest.mark.asyncio


def _hash_tree(root: Path, glob: str) -> dict[str, str]:
    out = {}
    for p in sorted(root.rglob(glob)):
        if p.is_symlink() or not p.is_file():
            continue
        out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


async def _client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


def _pick_enum_roundtrip(rules_cfg, tests_cfg) -> tuple[str, str, str]:
    """Resolve (field, valid_value, invalid_value) from config.
    field comes from tests_cfg.roundtrip; valid value comes from rules_cfg.enums."""
    field = tests_cfg["roundtrip"]["field"]
    if field not in rules_cfg["editable_fields"]:
        pytest.skip(f"tests.yaml roundtrip field '{field}' not in editable_fields")
    if rules_cfg["field_types"].get(field) != "enum":
        pytest.skip(f"tests.yaml roundtrip field '{field}' is not enum-typed")
    new = tests_cfg["roundtrip"]["new_value"]
    invalid = tests_cfg["roundtrip"]["invalid_value"]
    if new not in rules_cfg["enums"][field]:
        pytest.skip(f"new_value {new!r} not in enum {field}")
    return field, new, invalid


def _seed_one(isolated_content, rules_cfg, real_content_src) -> tuple[Path, str]:
    type_name = next(iter(rules_cfg["note_types"]))
    return make_note(
        content_root=isolated_content,
        real_content_src=real_content_src,
        rules_cfg=rules_cfg,
        type_name=type_name,
        folder_name="roundtrip-target",
    )


async def test_patch_persists_and_does_not_touch_other_files(
    isolated_content, rules_cfg, dashboard_cfg, tests_cfg, real_content_src, server_factory
):
    field, new_value, _invalid = _pick_enum_roundtrip(rules_cfg, tests_cfg)
    target, slug = _seed_one(isolated_content, rules_cfg, real_content_src)
    other_target, _ = make_note(
        content_root=isolated_content,
        real_content_src=real_content_src,
        rules_cfg=rules_cfg,
        type_name=list(rules_cfg["note_types"])[1],
        folder_name="should-not-change",
    )
    original_obj = json.loads(target.read_text())
    other_meta_before = _hash_tree(isolated_content, "index.meta.json")
    other_meta_before.pop(str(target.relative_to(isolated_content)))
    mdx_before = _hash_tree(isolated_content, "index.mdx")

    srv = server_factory()
    async with await _client(srv.app) as client:
        r = await client.patch(
            f"/api/notes/{slug}/field",
            data={"field": field, "value": new_value},
        )
    assert r.status_code == 200, f"unexpected status {r.status_code}: {r.text}"

    after_obj = json.loads(target.read_text())
    assert after_obj[field] == new_value, "PATCH did not persist new value"
    for k, v in original_obj.items():
        if k == field:
            continue
        assert after_obj[k] == v, f"PATCH mutated unrelated key '{k}'"

    other_meta_after = _hash_tree(isolated_content, "index.meta.json")
    other_meta_after.pop(str(target.relative_to(isolated_content)))
    assert other_meta_after == other_meta_before, "PATCH changed an unrelated index.meta.json"
    assert _hash_tree(isolated_content, "index.mdx") == mdx_before, "PATCH changed an MDX file"


async def test_patch_invalid_value_returns_422_and_leaves_file_intact(
    isolated_content, rules_cfg, tests_cfg, real_content_src, server_factory
):
    field, _good, invalid = _pick_enum_roundtrip(rules_cfg, tests_cfg)
    target, slug = _seed_one(isolated_content, rules_cfg, real_content_src)
    before = target.read_bytes()
    srv = server_factory()
    async with await _client(srv.app) as client:
        r = await client.patch(
            f"/api/notes/{slug}/field",
            data={"field": field, "value": invalid},
        )
    assert r.status_code == 422
    assert target.read_bytes() == before, "file changed despite 422 response"


async def test_patch_non_editable_field_returns_422(
    isolated_content, rules_cfg, real_content_src, server_factory
):
    target, slug = _seed_one(isolated_content, rules_cfg, real_content_src)
    non_editable = next(
        f for f in rules_cfg["mandatory_meta_keys"]
        if f not in rules_cfg["editable_fields"]
    )
    before = target.read_bytes()
    srv = server_factory()
    async with await _client(srv.app) as client:
        r = await client.patch(
            f"/api/notes/{slug}/field",
            data={"field": non_editable, "value": "anything"},
        )
    assert r.status_code == 422
    assert target.read_bytes() == before


async def test_patch_unknown_slug_returns_404(isolated_content, rules_cfg, real_content_src, server_factory):
    _seed_one(isolated_content, rules_cfg, real_content_src)
    srv = server_factory()
    async with await _client(srv.app) as client:
        r = await client.patch(
            "/api/notes/this/slug/does/not/exist/field",
            data={"field": "status", "value": "active"},
        )
    assert r.status_code == 404


async def test_patch_integer_field_persists_as_int(
    isolated_content, rules_cfg, real_content_src, server_factory
):
    int_field = next(
        (f for f, t in rules_cfg["field_types"].items()
         if t == "integer" and f in rules_cfg["editable_fields"]),
        None,
    )
    if int_field is None:
        pytest.skip("no integer-typed editable field in rules.yaml")
    target, slug = _seed_one(isolated_content, rules_cfg, real_content_src)
    cmin, cmax = rules_cfg.get("closure_score_range", [0, 7])
    target_value = max(cmin, min(cmax, 5))
    srv = server_factory()
    async with await _client(srv.app) as client:
        r = await client.patch(
            f"/api/notes/{slug}/field",
            data={"field": int_field, "value": str(target_value)},
        )
    assert r.status_code == 200
    obj = json.loads(target.read_text())
    assert obj[int_field] == target_value
    assert isinstance(obj[int_field], int)


async def test_patch_preserves_2_space_indent_and_trailing_newline(
    isolated_content, rules_cfg, tests_cfg, real_content_src, server_factory
):
    field, new_value, _ = _pick_enum_roundtrip(rules_cfg, tests_cfg)
    target, slug = _seed_one(isolated_content, rules_cfg, real_content_src)
    srv = server_factory()
    async with await _client(srv.app) as client:
        r = await client.patch(
            f"/api/notes/{slug}/field",
            data={"field": field, "value": new_value},
        )
    assert r.status_code == 200
    raw = target.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    for line in raw.splitlines():
        if line.startswith(" ") and not line.startswith("    "):
            assert line.startswith("  "), f"non-2-space indent line: {line!r}"
