"""Unit tests for scripts/writer.py.

Generates a single note from real templates, then exercises every writer
behavior on it. No fixture files involved.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tests.factory import make_note


def _hash_all(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_symlink() or not p.is_file():
            continue
        out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


@pytest.fixture
def target(isolated_content: Path, configured_env, rules_cfg, real_content_src) -> tuple[Path, str]:
    """A single freshly-generated note for the writer to operate on."""
    type_name = next(iter(rules_cfg["note_types"]))
    meta_path, slug = make_note(
        content_root=isolated_content,
        real_content_src=real_content_src,
        rules_cfg=rules_cfg,
        type_name=type_name,
        folder_name="writer-target",
    )
    return meta_path, slug


def _pick_enum_field(rules_cfg) -> tuple[str, str]:
    """Return (field_name, valid_value) for any enum-typed editable field."""
    for f, ftype in rules_cfg["field_types"].items():
        if ftype == "enum" and f in rules_cfg["editable_fields"]:
            allowed = rules_cfg["enums"].get(f, [])
            if allowed:
                return f, allowed[0]
    pytest.skip("no enum-typed editable field declared in rules.yaml")


def test_writer_persists_value(target, rules_cfg):
    from writer import write_field
    meta_path, _slug = target
    field, new_value = _pick_enum_field(rules_cfg)
    original = json.loads(meta_path.read_text())
    write_field(meta_path, field, new_value, rules_cfg)
    on_disk = json.loads(meta_path.read_text())
    assert on_disk[field] == new_value
    for k, v in original.items():
        if k == field:
            continue
        assert on_disk[k] == v, f"writer mutated unrelated key '{k}'"


def test_writer_preserves_2_space_indent_and_trailing_newline(target, rules_cfg):
    from writer import write_field
    meta_path, _slug = target
    field, new_value = _pick_enum_field(rules_cfg)
    write_field(meta_path, field, new_value, rules_cfg)
    raw = meta_path.read_text(encoding="utf-8")
    assert raw.endswith("\n"), "missing trailing newline"
    for line in raw.splitlines():
        if line.startswith(" ") and not line.startswith("    "):
            assert line.startswith("  "), f"non-2-space indent line: {line!r}"


def test_writer_does_not_touch_sibling_mdx(target, rules_cfg):
    from writer import write_field
    meta_path, _slug = target
    mdx = meta_path.with_name("index.mdx")
    before = mdx.read_bytes()
    field, new_value = _pick_enum_field(rules_cfg)
    write_field(meta_path, field, new_value, rules_cfg)
    assert mdx.read_bytes() == before


def test_writer_does_not_touch_other_files(isolated_content, target, rules_cfg, real_content_src):
    from writer import write_field
    meta_path, _slug = target
    other_type = list(rules_cfg["note_types"])[1]
    other_path, _other_slug = make_note(
        content_root=isolated_content,
        real_content_src=real_content_src,
        rules_cfg=rules_cfg,
        type_name=other_type,
        folder_name="other-note",
    )
    before = _hash_all(isolated_content)
    field, new_value = _pick_enum_field(rules_cfg)
    write_field(meta_path, field, new_value, rules_cfg)
    after = _hash_all(isolated_content)
    changed = {k for k in after if before.get(k) != after[k]}
    assert changed == {str(meta_path.relative_to(isolated_content))}, \
        f"writer touched files it should not have: {changed - {str(meta_path.relative_to(isolated_content))}}"


def test_writer_rejects_non_editable_field(target, rules_cfg):
    from writer import WriterError, write_field
    meta_path, _slug = target
    non_editable = next(
        f for f in rules_cfg["mandatory_meta_keys"]
        if f not in rules_cfg["editable_fields"]
    )
    with pytest.raises(WriterError):
        write_field(meta_path, non_editable, "anything", rules_cfg)


def test_writer_rejects_invalid_enum_and_leaves_file_intact(target, rules_cfg):
    from writer import WriterError, write_field
    meta_path, _slug = target
    field, _good = _pick_enum_field(rules_cfg)
    before = meta_path.read_bytes()
    with pytest.raises(WriterError):
        write_field(meta_path, field, "definitely-not-a-valid-enum-value", rules_cfg)
    assert meta_path.read_bytes() == before, "file changed despite invalid value"


def test_writer_rejects_bad_date_and_leaves_file_intact(target, rules_cfg):
    from writer import WriterError, write_field
    meta_path, _slug = target
    date_field = next(
        f for f, t in rules_cfg["field_types"].items()
        if t == "date" and f in rules_cfg["editable_fields"]
    )
    before = meta_path.read_bytes()
    with pytest.raises(WriterError):
        write_field(meta_path, date_field, "not-a-date", rules_cfg)
    assert meta_path.read_bytes() == before


def test_writer_rejects_closure_score_out_of_range(target, rules_cfg):
    from writer import WriterError, write_field
    meta_path, _slug = target
    if "closure_score" not in rules_cfg["editable_fields"]:
        pytest.skip("closure_score not editable in rules.yaml")
    cmin, cmax = rules_cfg["closure_score_range"]
    before = meta_path.read_bytes()
    with pytest.raises(WriterError):
        write_field(meta_path, "closure_score", cmax + 100, rules_cfg)
    assert meta_path.read_bytes() == before
