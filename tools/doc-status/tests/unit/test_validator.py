"""Unit tests for scripts/validator.py.

Each test generates the input it needs from the real templates, then
asserts the validator produces the expected issue type. Nothing here
hardcodes a slug, a heading, a type-specific path, or a reference date.

Determinism: overdue dates are built relative to date.today() in the
factory, and the validator also defaults to date.today() — so the two
are always in sync regardless of when the suite runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.factory import make_note, overdue_last_reviewed


def _validate(isolated_content, rules_cfg, dashboard_cfg):
    from scanner import scan
    from validator import validate
    return validate(scan(isolated_content, rules_cfg), rules_cfg, dashboard_cfg)


def _issue_types_for(report, slug):
    return {i.issue_type for i in report.summaries[slug].issues}


def test_template_baseline_is_clean_for_every_type(isolated_content, configured_env, rules_cfg, dashboard_cfg, real_content_src):
    """A note generated straight from the real template (with placeholders
    filled and required scalars defaulted) must NOT produce structural
    issues for any type."""
    structural = {"missing_mandatory", "invalid_id", "invalid_enum", "invalid_date", "heading_missing"}
    slugs_for_type = {}
    for type_name in rules_cfg["note_types"]:
        _meta_path, slug = make_note(
            content_root=isolated_content,
            real_content_src=real_content_src,
            rules_cfg=rules_cfg,
            type_name=type_name,
            folder_name=f"baseline-{type_name}",
        )
        slugs_for_type[type_name] = slug

    report = _validate(isolated_content, rules_cfg, dashboard_cfg)
    for type_name, slug in slugs_for_type.items():
        types = _issue_types_for(report, slug)
        bad = types & structural
        assert not bad, f"baseline {type_name} note had structural issues {bad}: {report.summaries[slug].issues}"


def test_missing_mandatory_key_is_flagged(isolated_content, configured_env, rules_cfg, dashboard_cfg, real_content_src):
    type_name = next(iter(rules_cfg["note_types"]))
    target_key = rules_cfg["mandatory_meta_keys"][0]
    _meta_path, slug = make_note(
        content_root=isolated_content,
        real_content_src=real_content_src,
        rules_cfg=rules_cfg,
        type_name=type_name,
        folder_name="missing-mandatory",
        omit_meta_keys=[target_key],
    )
    report = _validate(isolated_content, rules_cfg, dashboard_cfg)
    assert "missing_mandatory" in _issue_types_for(report, slug)


def test_invalid_enum_is_flagged(isolated_content, configured_env, rules_cfg, dashboard_cfg, real_content_src):
    enum_field, enum_values = next(iter(rules_cfg["enums"].items()))
    bad_value = "definitely-not-" + enum_values[0]
    type_name = next(iter(rules_cfg["note_types"]))
    _meta_path, slug = make_note(
        content_root=isolated_content,
        real_content_src=real_content_src,
        rules_cfg=rules_cfg,
        type_name=type_name,
        folder_name="bad-enum",
        meta_overrides={enum_field: bad_value},
    )
    report = _validate(isolated_content, rules_cfg, dashboard_cfg)
    assert "invalid_enum" in _issue_types_for(report, slug)


def test_invalid_id_is_flagged_for_every_type(isolated_content, configured_env, rules_cfg, dashboard_cfg, real_content_src):
    slugs = {}
    for type_name in rules_cfg["note_types"]:
        _meta_path, slug = make_note(
            content_root=isolated_content,
            real_content_src=real_content_src,
            rules_cfg=rules_cfg,
            type_name=type_name,
            folder_name=f"bad-id-{type_name}",
            meta_overrides={"id": "DEFINITELY-INVALID-ID-FORMAT"},
        )
        slugs[type_name] = slug
    report = _validate(isolated_content, rules_cfg, dashboard_cfg)
    for type_name, slug in slugs.items():
        assert "invalid_id" in _issue_types_for(report, slug), \
            f"{type_name}: invalid id not flagged (issues: {report.summaries[slug].issues})"


def test_overdue_warning_when_just_past_window(isolated_content, configured_env, rules_cfg, dashboard_cfg, real_content_src):
    # Pick a type that uses a real cycle (skip 'never')
    cycle = next(c for c in rules_cfg["staleness_days"] if c != "never")
    type_name = next(iter(rules_cfg["note_types"]))
    overdue_date = overdue_last_reviewed(rules_cfg, cycle, multiplier=1.5)
    _meta_path, slug = make_note(
        content_root=isolated_content,
        real_content_src=real_content_src,
        rules_cfg=rules_cfg,
        type_name=type_name,
        folder_name="overdue-warning",
        meta_overrides={"review_cycle": cycle, "last_reviewed": overdue_date},
    )
    report = _validate(isolated_content, rules_cfg, dashboard_cfg)
    types = _issue_types_for(report, slug)
    assert ("overdue_warning" in types) or ("overdue_error" in types), types


def test_overdue_error_when_far_past_window(isolated_content, configured_env, rules_cfg, dashboard_cfg, real_content_src):
    cycle = next(c for c in rules_cfg["staleness_days"] if c != "never")
    err_mult = float(rules_cfg["overdue_multipliers"]["error"]) + 1.0
    type_name = next(iter(rules_cfg["note_types"]))
    overdue_date = overdue_last_reviewed(rules_cfg, cycle, multiplier=err_mult)
    _meta_path, slug = make_note(
        content_root=isolated_content,
        real_content_src=real_content_src,
        rules_cfg=rules_cfg,
        type_name=type_name,
        folder_name="overdue-error",
        meta_overrides={"review_cycle": cycle, "last_reviewed": overdue_date},
    )
    report = _validate(isolated_content, rules_cfg, dashboard_cfg)
    assert "overdue_error" in _issue_types_for(report, slug)


def test_missing_heading_is_flagged_for_every_type(isolated_content, configured_env, rules_cfg, dashboard_cfg, real_content_src):
    """Drop ALL headings → every type must surface heading_missing."""
    if not rules_cfg.get("heading_check", {}).get("enabled"):
        pytest.skip("heading_check disabled in rules.yaml")
    slugs = {}
    for type_name in rules_cfg["note_types"]:
        _meta_path, slug = make_note(
            content_root=isolated_content,
            real_content_src=real_content_src,
            rules_cfg=rules_cfg,
            type_name=type_name,
            folder_name=f"no-headings-{type_name}",
            headings=[],
        )
        slugs[type_name] = slug
    report = _validate(isolated_content, rules_cfg, dashboard_cfg)
    for type_name, slug in slugs.items():
        # Some types may have empty templates (zero required headings) — only assert when the template HAS headings.
        scanned_template_headings = report.summaries[slug].issues
        # If template has at least one heading, the issue must appear.
        from scanner import scan
        scan_result = scan(isolated_content, rules_cfg)
        if scan_result.templates[type_name].headings:
            assert "heading_missing" in _issue_types_for(report, slug), \
                f"{type_name}: missing-heading not flagged"


def test_color_buckets_are_drawn_from_dashboard_yaml(isolated_content, configured_env, rules_cfg, dashboard_cfg, real_content_src):
    type_name = next(iter(rules_cfg["note_types"]))
    make_note(
        content_root=isolated_content,
        real_content_src=real_content_src,
        rules_cfg=rules_cfg,
        type_name=type_name,
        folder_name="bucket-check",
    )
    report = _validate(isolated_content, rules_cfg, dashboard_cfg)
    allowed = {b["id"] for b in dashboard_cfg["color_buckets"]}
    for s in report.summaries.values():
        assert s.bucket_id in allowed
