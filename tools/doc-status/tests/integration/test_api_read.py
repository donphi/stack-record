"""Integration tests: read-only HTTP endpoints.

Each test generates the notes it needs from the real templates, then
boots a fresh server pointed at that tree.
"""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from tests.factory import make_note


pytestmark = pytest.mark.asyncio


async def _client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


def _make_one_per_type(isolated_content, rules_cfg, real_content_src) -> dict[str, str]:
    """Return {type: slug} for one healthy note of every type."""
    out = {}
    for type_name in rules_cfg["note_types"]:
        _meta_path, slug = make_note(
            content_root=isolated_content,
            real_content_src=real_content_src,
            rules_cfg=rules_cfg,
            type_name=type_name,
            folder_name=f"sample-{type_name}",
        )
        out[type_name] = slug
    return out


async def test_index_renders_every_generated_note(isolated_content, rules_cfg, real_content_src, server_factory):
    slugs_by_type = _make_one_per_type(isolated_content, rules_cfg, real_content_src)
    srv = server_factory()
    async with await _client(srv.app) as client:
        r = await client.get("/")
    assert r.status_code == 200
    for type_name, slug in slugs_by_type.items():
        # The slug derives from the folder, so the generated folder name
        # appears in the page somewhere (slug column or anchor id).
        assert slug.split("/")[-1] in r.text, f"missing {type_name} slug: {slug}"


async def test_filter_by_type_only_returns_that_type(isolated_content, rules_cfg, real_content_src, server_factory):
    slugs_by_type = _make_one_per_type(isolated_content, rules_cfg, real_content_src)
    target_type = next(iter(slugs_by_type))
    other_types = [t for t in slugs_by_type if t != target_type]
    srv = server_factory()
    async with await _client(srv.app) as client:
        r = await client.get("/api/table", params={"type": target_type})
    assert r.status_code == 200
    assert slugs_by_type[target_type].split("/")[-1] in r.text
    for other in other_types:
        assert slugs_by_type[other].split("/")[-1] not in r.text


async def test_search_by_title(isolated_content, rules_cfg, real_content_src, server_factory):
    type_name = next(iter(rules_cfg["note_types"]))
    distinctive_title = "Zxqv-Distinctive-Title-1234"
    _meta_path, slug = make_note(
        content_root=isolated_content,
        real_content_src=real_content_src,
        rules_cfg=rules_cfg,
        type_name=type_name,
        folder_name="searchable",
        meta_overrides={"title": distinctive_title},
    )
    srv = server_factory()
    async with await _client(srv.app) as client:
        r = await client.get("/api/table", params={"q": "Zxqv"})
    assert r.status_code == 200
    assert distinctive_title in r.text


async def test_overdue_preset_lists_only_overdue_notes(isolated_content, rules_cfg, real_content_src, server_factory):
    from tests.factory import overdue_last_reviewed
    cycle = next(c for c in rules_cfg["staleness_days"] if c != "never")
    type_name = next(iter(rules_cfg["note_types"]))
    _, fresh_slug = make_note(
        content_root=isolated_content, real_content_src=real_content_src,
        rules_cfg=rules_cfg, type_name=type_name, folder_name="fresh",
    )
    _, overdue_slug = make_note(
        content_root=isolated_content, real_content_src=real_content_src,
        rules_cfg=rules_cfg, type_name=type_name, folder_name="stale",
        meta_overrides={"review_cycle": cycle, "last_reviewed": overdue_last_reviewed(rules_cfg, cycle, 1.5)},
    )
    srv = server_factory()
    async with await _client(srv.app) as client:
        r = await client.get("/api/table", params={"preset": "overdue"})
    assert r.status_code == 200
    assert overdue_slug.split("/")[-1] in r.text
    assert fresh_slug.split("/")[-1] not in r.text


async def test_sort_by_overdue_desc_puts_most_overdue_first(isolated_content, rules_cfg, dashboard_cfg, real_content_src, server_factory):
    """Verify the sortable_columns config drives table ordering."""
    from tests.factory import overdue_last_reviewed
    cycle = next(c for c in rules_cfg["staleness_days"] if c != "never")
    type_name = next(iter(rules_cfg["note_types"]))

    sortable = {c["id"]: c for c in dashboard_cfg.get("sortable_columns", [])}
    if "days_overdue" not in sortable:
        pytest.skip("days_overdue not configured as sortable in dashboard.yaml")

    _, slug_small = make_note(
        content_root=isolated_content, real_content_src=real_content_src,
        rules_cfg=rules_cfg, type_name=type_name, folder_name="small-overdue",
        meta_overrides={"review_cycle": cycle, "last_reviewed": overdue_last_reviewed(rules_cfg, cycle, 1.2)},
    )
    _, slug_huge = make_note(
        content_root=isolated_content, real_content_src=real_content_src,
        rules_cfg=rules_cfg, type_name=type_name, folder_name="huge-overdue",
        meta_overrides={"review_cycle": cycle, "last_reviewed": overdue_last_reviewed(rules_cfg, cycle, 5.0)},
    )
    srv = server_factory()
    async with await _client(srv.app) as client:
        r = await client.get("/api/table", params={"sort": "days_overdue", "dir": "desc"})
    assert r.status_code == 200
    body = r.text
    pos_huge = body.find(slug_huge.split("/")[-1])
    pos_small = body.find(slug_small.split("/")[-1])
    assert pos_huge != -1 and pos_small != -1
    assert pos_huge < pos_small, "desc sort should put the more-overdue note first"


async def test_sort_asc_inverts_order(isolated_content, rules_cfg, dashboard_cfg, real_content_src, server_factory):
    type_name = next(iter(rules_cfg["note_types"]))
    sortable = {c["id"]: c for c in dashboard_cfg.get("sortable_columns", [])}
    if "issues" not in sortable:
        pytest.skip("issues not configured as sortable in dashboard.yaml")

    _, slug_clean = make_note(
        content_root=isolated_content, real_content_src=real_content_src,
        rules_cfg=rules_cfg, type_name=type_name, folder_name="clean-note",
    )
    _, slug_broken = make_note(
        content_root=isolated_content, real_content_src=real_content_src,
        rules_cfg=rules_cfg, type_name=type_name, folder_name="broken-note",
        meta_overrides={"id": "DEFINITELY-INVALID"},
    )
    srv = server_factory()
    async with await _client(srv.app) as client:
        r_desc = await client.get("/api/table", params={"sort": "issues", "dir": "desc"})
        r_asc = await client.get("/api/table", params={"sort": "issues", "dir": "asc"})
    assert r_desc.status_code == 200 and r_asc.status_code == 200
    desc_broken = r_desc.text.find(slug_broken.split("/")[-1])
    desc_clean = r_desc.text.find(slug_clean.split("/")[-1])
    asc_broken = r_asc.text.find(slug_broken.split("/")[-1])
    asc_clean = r_asc.text.find(slug_clean.split("/")[-1])
    assert desc_broken < desc_clean, "desc by issues: broken (more issues) should come first"
    assert asc_clean < asc_broken, "asc by issues: clean (fewer issues) should come first"


async def test_refresh_picks_up_external_edits(isolated_content, rules_cfg, real_content_src, server_factory):
    """External edit + /?refresh=1 → dashboard shows new value."""
    type_name = next(iter(rules_cfg["note_types"]))
    enum_field, allowed_values = next(
        (f, rules_cfg["enums"][f]) for f, t in rules_cfg["field_types"].items()
        if t == "enum" and f in rules_cfg["editable_fields"] and f in rules_cfg["enums"]
    )
    initial = allowed_values[0]
    later = next(v for v in allowed_values if v != initial)
    meta_path, _slug = make_note(
        content_root=isolated_content, real_content_src=real_content_src,
        rules_cfg=rules_cfg, type_name=type_name, folder_name="refreshable",
        meta_overrides={enum_field: initial},
    )
    srv = server_factory()
    async with await _client(srv.app) as client:
        r1 = await client.get("/")
        assert r1.status_code == 200
        assert initial in r1.text

        meta = json.loads(meta_path.read_text())
        meta[enum_field] = later
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

        r2 = await client.get("/", params={"refresh": "1"})
        assert r2.status_code == 200
        assert later in r2.text
