"""Unit tests for scripts/scanner.py.

Notes are generated programmatically from the REAL per-type templates.
Adding a new note type or folder to content-src/docs/ requires zero
changes here — we iterate rules.yaml.note_types and assert behaviors,
not specific paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.factory import make_note


def test_scanner_loads_every_type_from_real_templates(isolated_content: Path, configured_env, rules_cfg, real_content_src):
    from scanner import scan
    result = scan(isolated_content, rules_cfg)
    expected = set(rules_cfg["note_types"].keys())
    assert set(result.templates.keys()) == expected, \
        "scanner did not load a template for every type declared in rules.yaml"


def test_scanner_skips_template_dirs(isolated_content: Path, configured_env, rules_cfg, real_content_src):
    from scanner import scan
    for type_name in rules_cfg["note_types"]:
        make_note(
            content_root=isolated_content,
            real_content_src=real_content_src,
            rules_cfg=rules_cfg,
            type_name=type_name,
            folder_name=f"sample-{type_name}",
        )
    result = scan(isolated_content, rules_cfg)
    for slug in result.notes:
        assert "_template" not in slug, f"scanner picked up a template note: {slug}"


def test_scanner_finds_every_generated_note(isolated_content: Path, configured_env, rules_cfg, real_content_src):
    from scanner import scan
    expected_slugs = set()
    for type_name in rules_cfg["note_types"]:
        _meta_path, slug = make_note(
            content_root=isolated_content,
            real_content_src=real_content_src,
            rules_cfg=rules_cfg,
            type_name=type_name,
            folder_name=f"sample-{type_name}",
        )
        expected_slugs.add(slug)
    result = scan(isolated_content, rules_cfg)
    assert expected_slugs.issubset(result.notes.keys())


def test_scanner_extracts_headings_in_order(isolated_content: Path, configured_env, rules_cfg, real_content_src):
    from scanner import scan
    custom_headings = ["First", "Second", "Third"]
    type_name = next(iter(rules_cfg["note_types"]))
    _meta_path, slug = make_note(
        content_root=isolated_content,
        real_content_src=real_content_src,
        rules_cfg=rules_cfg,
        type_name=type_name,
        folder_name="ordered",
        headings=custom_headings,
    )
    result = scan(isolated_content, rules_cfg)
    assert result.notes[slug].headings == custom_headings


def test_scanner_records_raw_bytes_for_writeback_diffing(isolated_content: Path, configured_env, rules_cfg, real_content_src):
    from scanner import scan
    type_name = next(iter(rules_cfg["note_types"]))
    meta_path, slug = make_note(
        content_root=isolated_content,
        real_content_src=real_content_src,
        rules_cfg=rules_cfg,
        type_name=type_name,
        folder_name="raw-bytes-check",
    )
    result = scan(isolated_content, rules_cfg)
    assert result.notes[slug].meta_raw_bytes == meta_path.read_bytes()


def test_slug_strips_folder_groups(isolated_content: Path, configured_env, rules_cfg, real_content_src):
    """The scanner derives a slug by stripping (xx-foo) Fumadocs groups."""
    from scanner import slug_from_rel_dir
    assert "(" not in slug_from_rel_dir("(01-navigation)/maps/x")
    assert slug_from_rel_dir("") == ""
    assert slug_from_rel_dir("(99-anything)/x/y") == "x/y"
