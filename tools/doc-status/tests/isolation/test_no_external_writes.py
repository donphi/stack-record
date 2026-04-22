"""
Isolation test — directly addresses "make sure other tools/* and the
real content tree are not affected".

Hashes every file under each isolation root from `config/tests.yaml`
before and after a doc-status workflow that includes scanning,
validating, writing fields, rendering static HTML, and rendering markdown.

If any external file changes, the assertion fires with a list of
changed paths. The Docker `test` service additionally mounts these
roots read-only, so this test is belt-and-suspenders.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.conftest import hash_tree
from tests.factory import make_note


def _existing_roots(tests_cfg) -> list[Path]:
    return [Path(p) for p in tests_cfg["isolation_roots"] if Path(p).exists()]


def test_external_files_unchanged_after_full_workflow(
    isolated_content, configured_env, tests_cfg, rules_cfg, dashboard_cfg, real_content_src, monkeypatch
):
    roots = _existing_roots(tests_cfg)
    if not roots:
        pytest.skip("No isolation roots exist (expected only in the docker `test` service)")

    before = {str(r): hash_tree(r) for r in roots}

    type_name = next(iter(rules_cfg["note_types"]))
    target, _slug = make_note(
        content_root=isolated_content,
        real_content_src=real_content_src,
        rules_cfg=rules_cfg,
        type_name=type_name,
        folder_name="isolation-target",
    )

    from scanner import scan
    from validator import validate
    from writer import write_field
    import render_static
    import render_report

    sresult = scan(isolated_content, rules_cfg)
    validate(sresult, rules_cfg, dashboard_cfg)

    enum_field, allowed = next(
        (f, rules_cfg["enums"][f]) for f, t in rules_cfg["field_types"].items()
        if t == "enum" and f in rules_cfg["editable_fields"] and f in rules_cfg["enums"]
    )
    write_field(target, enum_field, allowed[0], rules_cfg)

    out_dir = isolated_content.parent / "isolation-output"
    out_dir.mkdir(exist_ok=True)
    monkeypatch.setitem(dashboard_cfg["paths"], "output_html", str(out_dir / "dashboard.html"))
    monkeypatch.setitem(dashboard_cfg["paths"], "output_md", str(out_dir / "report.md"))
    monkeypatch.setattr(render_static, "load_dashboard_config", lambda: dashboard_cfg)
    monkeypatch.setattr(render_report, "load_dashboard_config", lambda: dashboard_cfg)
    render_static.main()
    render_report.main()

    after = {str(r): hash_tree(r) for r in roots}

    diffs = {}
    for root_str in before:
        b = before[root_str]
        a = after[root_str]
        changed = {p for p in set(a) | set(b) if a.get(p) != b.get(p)}
        if changed:
            diffs[root_str] = sorted(changed)

    assert not diffs, f"doc-status modified files outside its sandbox: {json.dumps(diffs, indent=2)}"
